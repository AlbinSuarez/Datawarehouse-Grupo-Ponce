"""
Servicio Analítico para el Data Mart de Inventarios y Abastecimiento
Calcula Valoración en USD, Rotación (Turnover), Días de Inventario (DIO),
Stock de Seguridad, Quiebres de Stock (Stockouts) y Semáforo de Salud
con soporte para Clasificación de SKU: MP (Materia Prima), ME (Material de Empaque) y PT (Producto Terminado).
"""

from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from db import db_engine

class InventoryAnalyticsService:
    def __init__(self):
        self.df_inventory = pd.DataFrame()
        self.df_by_location = pd.DataFrame()
        self.df_locations = pd.DataFrame()
        self.latest_fx = 1.0
        self._load_inventory_data()

    def _load_inventory_data(self):
        try:
            conn = db_engine.get_connection()
            
            # 1. Tasa de cambio USD-VENTAS
            df_fx = pd.read_sql("""
                SELECT TOP 1 CAST(XCHGRATE AS FLOAT) as latest_rate
                FROM DYNAMICS.dbo.MC00100
                WHERE EXGTBLID = 'USD-VENTAS' AND XCHGRATE > 0
                ORDER BY EXCHDATE DESC
            """, conn)
            latest_fx = df_fx.iloc[0]['latest_rate'] if not df_fx.empty else 1.0

            # 2. Stock por Artículo y Almacén
            df_stock = pd.read_sql("""
                SELECT 
                    RTRIM(s.ITEMNMBR) as item_number,
                    RTRIM(i.ITEMDESC) as item_description,
                    COALESCE(NULLIF(RTRIM(i.ITMCLSCD), ''), 'GENERAL') as category,
                    COALESCE(NULLIF(RTRIM(s.LOCNCODE), ''), 'TOTAL_GENERAL') as location_code,
                    s.RCRDTYPE as record_type,
                    CAST(s.QTYONHND AS FLOAT) as qty_on_hand,
                    CAST(s.ATYALLOC AS FLOAT) as qty_allocated,
                    CAST(s.QTYONHND - s.ATYALLOC AS FLOAT) as qty_available,
                    CAST(s.QTYONORD AS FLOAT) as qty_on_order,
                    CAST(s.SFTYSTCKQTY AS FLOAT) as safety_stock,
                    CAST(s.ORDRPNTQTY AS FLOAT) as reorder_point,
                    CAST(COALESCE(NULLIF(i.CURRCOST, 0), i.STNDCOST, 0) AS FLOAT) as unit_cost_vef
                FROM PB.dbo.IV00102 s
                INNER JOIN PB.dbo.IV00101 i ON s.ITEMNMBR = i.ITEMNMBR
            """, conn)

            # 3. COGS anualizado y unidades vendidas de los últimos 12 meses
            df_sales_cogs = pd.read_sql("""
                SELECT 
                    RTRIM(l.ITEMNMBR) as item_number,
                    SUM(CASE WHEN h.SOPTYPE = 4 THEN -1.0 ELSE 1.0 END * l.QUANTITY) as annual_units_sold,
                    SUM(CASE WHEN h.SOPTYPE = 4 THEN -1.0 ELSE 1.0 END * l.EXTDCOST) as annual_cogs_vef
                FROM PB.dbo.SOP30200 h
                INNER JOIN PB.dbo.SOP30300 l ON h.SOPTYPE = l.SOPTYPE AND h.SOPNUMBE = l.SOPNUMBE
                WHERE h.SOPTYPE IN (3, 4) AND h.VOIDSTTS = 0
                  AND h.DOCDATE >= DATEADD(month, -12, GETDATE())
                GROUP BY l.ITEMNMBR
            """, conn)
            
            # 4. Almacenes
            df_locs = pd.read_sql("""
                SELECT 
                    COALESCE(NULLIF(RTRIM(LOCNCODE), ''), 'TOTAL_GENERAL') as location_code,
                    COALESCE(NULLIF(RTRIM(LOCNDSCR), ''), 'Almacén General') as location_name
                FROM PB.dbo.IV40700
            """, conn)
            conn.close()

            # Merge
            df_total = df_stock[df_stock['record_type'] == 1].copy()
            merged = df_total.merge(df_sales_cogs, on='item_number', how='left').fillna(0)
            
            # Cálculos en USD
            merged['unit_cost_usd'] = np.round(merged['unit_cost_vef'] / latest_fx, 4)
            merged['total_valuation_usd'] = np.round(merged['qty_on_hand'] * merged['unit_cost_usd'], 2)
            merged['annual_cogs_usd'] = np.round(merged['annual_cogs_vef'] / latest_fx, 2)
            
            # Clasificación de SKU: MP, ME y PT
            def classify_sku_type(cat):
                c = str(cat).strip().upper()
                if c == 'MP':
                    return 'MP'
                elif c == 'ME':
                    return 'ME'
                else:
                    return 'PT'

            def classify_sku_desc(cat):
                c = str(cat).strip().upper()
                if c == 'MP':
                    return 'MP - Materia Prima'
                elif c == 'ME':
                    return 'ME - Material de Empaque'
                else:
                    return 'PT - Producto Terminado'

            merged['sku_type'] = merged['category'].apply(classify_sku_type)
            merged['sku_type_desc'] = merged['category'].apply(classify_sku_desc)

            merged['inventory_turnover'] = np.where(
                merged['total_valuation_usd'] > 0,
                np.round(merged['annual_cogs_usd'] / merged['total_valuation_usd'], 2),
                0.0
            )
            
            daily_cogs = merged['annual_cogs_usd'] / 365.0
            merged['dio'] = np.where(
                daily_cogs > 0,
                np.round(merged['total_valuation_usd'] / daily_cogs, 1),
                999.0
            )

            def classify_health(r):
                if r['qty_available'] <= 0 and r['annual_units_sold'] > 0:
                    return "Quiebre de Stock (Stockout)"
                elif r['qty_available'] < r['safety_stock'] or (r['annual_cogs_usd'] > 0 and r['dio'] < 15):
                    return "Riesgo Crítico"
                elif r['dio'] > 180 or r['annual_cogs_usd'] == 0:
                    return "Sobreinventario"
                else:
                    return "Nivel Óptimo"

            merged['health_status'] = merged.apply(classify_health, axis=1)

            self.df_inventory = merged
            
            # Stock por almacén con SKU Type
            df_by_loc = df_stock[df_stock['record_type'] == 2].copy()
            df_by_loc['sku_type'] = df_by_loc['category'].apply(classify_sku_type)
            self.df_by_location = df_by_loc
            
            self.df_locations = df_locs
            self.latest_fx = latest_fx
            print(f"InventoryAnalyticsService inicializado con {len(self.df_inventory)} artículos (MP, ME, PT) a {latest_fx:.2f} VEF/USD.")
        except Exception as e:
            print(f"Error cargando datos de inventario: {e}")

    def _filter_sku(self, df, sku_type="ALL", category="ALL"):
        filtered = df.copy()
        if sku_type and sku_type != "ALL":
            filtered = filtered[filtered["sku_type"] == sku_type]
        if category and category != "ALL":
            filtered = filtered[filtered["category"] == category]
        return filtered

    def get_inventory_kpis(self, sku_type="ALL", category="ALL"):
        df = self._filter_sku(self.df_inventory, sku_type, category)

        total_val = float(df["total_valuation_usd"].sum())
        total_cogs = float(df["annual_cogs_usd"].sum())
        total_units_on_hand = float(df["qty_on_hand"].sum())
        total_units_on_order = float(df["qty_on_order"].sum())
        
        turnover = round(total_cogs / total_val, 2) if total_val > 0 else 0.0
        dio = round(365.0 / turnover, 1) if turnover > 0 else 0.0

        stockouts = int((df["health_status"] == "Quiebre de Stock (Stockout)").sum())
        at_risk = int((df["health_status"] == "Riesgo Crítico").sum())
        optimal = int((df["health_status"] == "Nivel Óptimo").sum())
        excess = int((df["health_status"] == "Sobreinventario").sum())

        return {
            "total_valuation_usd": total_val,
            "annual_cogs_usd": total_cogs,
            "total_units_on_hand": total_units_on_hand,
            "total_units_on_order": total_units_on_order,
            "inventory_turnover": turnover,
            "days_inventory_outstanding": dio,
            "stockout_items_count": stockouts,
            "at_risk_items_count": at_risk,
            "optimal_items_count": optimal,
            "excess_items_count": excess,
            "total_items_catalog": len(df),
            "exchange_rate_applied": self.latest_fx,
            "sku_type_filter": sku_type
        }

    def get_inventory_by_category(self, sku_type="ALL"):
        df = self._filter_sku(self.df_inventory, sku_type)
        grouped = df.groupby("category").agg(
            total_valuation_usd=("total_valuation_usd", "sum"),
            annual_cogs_usd=("annual_cogs_usd", "sum"),
            items_count=("item_number", "count"),
            qty_on_hand=("qty_on_hand", "sum")
        ).reset_index()

        grouped["total_valuation_usd"] = grouped["total_valuation_usd"].round(2)
        grouped["annual_cogs_usd"] = grouped["annual_cogs_usd"].round(2)
        grouped["turnover"] = np.where(
            grouped["total_valuation_usd"] > 0,
            (grouped["annual_cogs_usd"] / grouped["total_valuation_usd"]).round(2),
            0.0
        )
        grouped.sort_values(by="total_valuation_usd", ascending=False, inplace=True)
        return grouped.to_dict(orient="records")

    def get_inventory_by_location(self, sku_type="ALL"):
        df = self.df_by_location.copy()
        if sku_type and sku_type != "ALL":
            df = df[df["sku_type"] == sku_type]
            
        df['unit_cost_usd'] = df['unit_cost_vef'] / self.latest_fx
        df['valuation_usd'] = np.round(df['qty_on_hand'] * df['unit_cost_usd'], 2)
        
        grouped = df.groupby("location_code").agg(
            total_valuation_usd=("valuation_usd", "sum"),
            total_qty_on_hand=("qty_on_hand", "sum"),
            items_count=("item_number", "nunique")
        ).reset_index()

        grouped = grouped[grouped["total_valuation_usd"] > 0]
        grouped.sort_values(by="total_valuation_usd", ascending=False, inplace=True)
        return grouped.to_dict(orient="records")

    def get_health_summary(self, sku_type="ALL", category="ALL"):
        df = self._filter_sku(self.df_inventory, sku_type, category)
        summary = df.groupby("health_status").agg(
            items_count=("item_number", "count"),
            valuation_usd=("total_valuation_usd", "sum")
        ).reset_index()
        summary["valuation_usd"] = summary["valuation_usd"].round(2)
        return summary.to_dict(orient="records")

    def get_items_directory(self, sku_type="ALL", category="ALL", health_status="ALL"):
        df = self._filter_sku(self.df_inventory, sku_type, category)
        if health_status and health_status != "ALL":
            df = df[df["health_status"] == health_status]

        df_sorted = df.sort_values(by="total_valuation_usd", ascending=False)
        return df_sorted.to_dict(orient="records")

inv_service = InventoryAnalyticsService()
