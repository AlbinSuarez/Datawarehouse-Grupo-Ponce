import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from db import db_engine

class ReceivablesAnalyticsService:
    def __init__(self):
        self.df_ar = pd.DataFrame()
        self.sales_90d_usd = 1.0
        self.latest_fx = 1.0
        self._load_ar_data()

    def _load_ar_data(self):
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

            # 2. Documentos Abiertos en RM20101
            df_ar = pd.read_sql("""
                SELECT 
                    RTRIM(ar.CUSTNMBR) as customer_id,
                    RTRIM(c.CUSTNAME) as customer_name,
                    COALESCE(NULLIF(RTRIM(c.CUSTCLAS), ''), 'GENERAL') as customer_class_id,
                    RTRIM(ar.DOCNUMBR) as doc_number,
                    ar.RMDTYPAL as doc_type,
                    CASE ar.RMDTYPAL
                        WHEN 1 THEN 'Factura'
                        WHEN 3 THEN 'Nota de Débito'
                        WHEN 7 THEN 'Nota de Crédito (-)'
                        WHEN 8 THEN 'Cobro no Aplicado (-)'
                        WHEN 9 THEN 'Devolución (-)'
                        ELSE 'Otro'
                    END as doc_type_desc,
                    CAST(ar.DOCDATE AS DATE) as doc_date,
                    CAST(ar.DUEDATE AS DATE) as due_date,
                    CAST(ar.ORTRXAMT AS FLOAT) as orig_amount_vef,
                    CAST(ar.CURTRXAM AS FLOAT) as current_balance_vef,
                    RTRIM(ar.CURNCYID) as currency_id,
                    COALESCE(NULLIF(LTRIM(RTRIM(RTRIM(sp.SLPRSNFN) + ' ' + RTRIM(sp.SPRSNSLN))), ''), RTRIM(ar.SLPRSNID), 'No Asignado') as salesperson_name,
                    COALESCE(NULLIF(RTRIM(t.SLTERDSC), ''), NULLIF(RTRIM(t_sp.SLTERDSC), ''), 'Sin Zona') as territory_name,
                    CAST(COALESCE(c.CRLMTAMT, 0) AS FLOAT) as credit_limit_vef
                FROM PB.dbo.RM20101 ar
                LEFT JOIN PB.dbo.RM00101 c ON ar.CUSTNMBR = c.CUSTNMBR
                LEFT JOIN PB.dbo.RM00301 sp ON ar.SLPRSNID = sp.SLPRSNID
                LEFT JOIN PB.dbo.RM00303 t ON ar.SLSTERCD = t.SALSTERR
                LEFT JOIN PB.dbo.RM00303 t_sp ON sp.SALSTERR = t_sp.SALSTERR
                WHERE ar.CURTRXAM > 0 AND ar.VOIDSTTS = 0
            """, conn)

            # 3. Ventas de los últimos 90 días para DSO
            df_sales_90d = pd.read_sql("""
                SELECT 
                    SUM(CASE WHEN h.SOPTYPE = 4 THEN -1.0 ELSE 1.0 END * (l.XTNDPRCE - COALESCE(l.MRKDNAMT, 0))) as sales_90d_vef
                FROM PB.dbo.SOP30200 h
                INNER JOIN PB.dbo.SOP30300 l ON h.SOPTYPE = l.SOPTYPE AND h.SOPNUMBE = l.SOPNUMBE
                WHERE h.SOPTYPE IN (3, 4) AND h.VOIDSTTS = 0
                  AND h.DOCDATE >= DATEADD(day, -90, GETDATE())
            """, conn)
            sales_90d_usd = (df_sales_90d.iloc[0]['sales_90d_vef'] / latest_fx) if not df_sales_90d.empty else 1.0
            conn.close()

            # Conversión y cálculos
            mult = np.where(df_ar['doc_type'].isin([7, 8, 9]), -1.0, 1.0)
            df_ar['balance_usd'] = np.round((df_ar['current_balance_vef'] / latest_fx) * mult, 2)
            df_ar['orig_amount_usd'] = np.round((df_ar['orig_amount_vef'] / latest_fx) * mult, 2)
            df_ar['credit_limit_usd'] = np.round(df_ar['credit_limit_vef'] / latest_fx, 2)

            now = datetime.now().date()
            df_ar['due_date_dt'] = pd.to_datetime(df_ar['due_date']).dt.date
            df_ar['doc_date_dt'] = pd.to_datetime(df_ar['doc_date']).dt.date
            df_ar['overdue_days'] = (now - df_ar['due_date_dt']).apply(lambda x: x.days if pd.notnull(x) else 0)

            def classify_aging(row):
                days = row['overdue_days']
                if days <= 0:
                    return "Corriente / Al Día"
                elif days <= 30:
                    return "Vencido 1-30 Días"
                elif days <= 60:
                    return "Vencido 31-60 Días"
                elif days <= 90:
                    return "Vencido 61-90 Días"
                else:
                    return "Vencido >90 Días"

            df_ar['aging_bucket'] = df_ar.apply(classify_aging, axis=1)
            df_ar['is_overdue'] = np.where(df_ar['overdue_days'] > 0, 1, 0)

            self.df_ar = df_ar
            self.sales_90d_usd = sales_90d_usd
            self.latest_fx = latest_fx
            print(f"ReceivablesAnalyticsService inicializado con {len(self.df_ar)} documentos abiertos valorizados a {latest_fx:.2f} VEF/USD.")
        except Exception as e:
            print(f"Error cargando datos de cuentas por cobrar: {e}")

    def _apply_filters(self, df, territory="ALL", customer_class="ALL", salesperson="ALL"):
        filtered = df.copy()
        if territory and territory != "ALL":
            filtered = filtered[filtered["territory_name"] == territory]
        if customer_class and customer_class != "ALL":
            filtered = filtered[filtered["customer_class_id"] == customer_class]
        if salesperson and salesperson != "ALL":
            filtered = filtered[filtered["salesperson_name"] == salesperson]
        return filtered

    def get_ar_kpis(self, territory="ALL", customer_class="ALL", salesperson="ALL"):
        df = self._apply_filters(self.df_ar, territory, customer_class, salesperson)

        total_ar = float(df["balance_usd"].sum())
        
        overdue_df = df[df["overdue_days"] > 0]
        total_overdue = float(overdue_df[overdue_df["balance_usd"] > 0]["balance_usd"].sum())
        
        current_df = df[df["overdue_days"] <= 0]
        total_current = float(current_df[current_df["balance_usd"] > 0]["balance_usd"].sum())

        delinquency_rate = round((total_overdue / total_ar * 100), 2) if total_ar > 0 else 0.0
        dso = round((total_ar / self.sales_90d_usd) * 90, 1) if self.sales_90d_usd > 0 else 0.0

        total_custs_debt = int(df[df["balance_usd"] > 0]["customer_id"].nunique())
        total_open_invoices = int(df["doc_number"].nunique())

        return {
            "total_ar_balance_usd": total_ar,
            "total_overdue_usd": total_overdue,
            "total_current_usd": total_current,
            "delinquency_rate_pct": delinquency_rate,
            "dso_days": dso,
            "customers_with_debt_count": total_custs_debt,
            "open_documents_count": total_open_invoices,
            "sales_90d_usd": self.sales_90d_usd,
            "exchange_rate_applied": self.latest_fx
        }

    def get_aging_summary(self, territory="ALL", customer_class="ALL", salesperson="ALL"):
        df = self._apply_filters(self.df_ar, territory, customer_class, salesperson)
        
        grouped = df.groupby("aging_bucket").agg(
            docs_count=("doc_number", "count"),
            total_balance_usd=("balance_usd", "sum")
        ).reset_index()

        grouped["total_balance_usd"] = grouped["total_balance_usd"].round(2)
        
        bucket_order = ["Corriente / Al Día", "Vencido 1-30 Días", "Vencido 31-60 Días", "Vencido 61-90 Días", "Vencido >90 Días"]
        grouped['sort_idx'] = grouped['aging_bucket'].apply(lambda x: bucket_order.index(x) if x in bucket_order else 99)
        grouped.sort_values(by='sort_idx', inplace=True)
        grouped.drop(columns=['sort_idx'], inplace=True)

        return grouped.to_dict(orient="records")

    def get_ar_by_territory(self):
        grouped = self.df_ar.groupby("territory_name").agg(
            total_ar_usd=("balance_usd", "sum"),
            overdue_usd=("balance_usd", lambda x: x[self.df_ar.loc[x.index, 'overdue_days'] > 0].sum()),
            customers_count=("customer_id", "nunique"),
            docs_count=("doc_number", "count")
        ).reset_index()

        grouped["total_ar_usd"] = grouped["total_ar_usd"].round(2)
        grouped["overdue_usd"] = grouped["overdue_usd"].round(2)
        grouped["delinquency_pct"] = np.where(
            grouped["total_ar_usd"] > 0,
            (grouped["overdue_usd"] / grouped["total_ar_usd"] * 100).round(1),
            0.0
        )
        grouped.sort_values(by="total_ar_usd", ascending=False, inplace=True)
        return grouped.to_dict(orient="records")

    def get_ar_by_salesperson(self):
        grouped = self.df_ar.groupby("salesperson_name").agg(
            total_ar_usd=("balance_usd", "sum"),
            overdue_usd=("balance_usd", lambda x: x[self.df_ar.loc[x.index, 'overdue_days'] > 0].sum()),
            customers_count=("customer_id", "nunique"),
            docs_count=("doc_number", "count")
        ).reset_index()

        grouped["total_ar_usd"] = grouped["total_ar_usd"].round(2)
        grouped["overdue_usd"] = grouped["overdue_usd"].round(2)
        grouped["delinquency_pct"] = np.where(
            grouped["total_ar_usd"] > 0,
            (grouped["overdue_usd"] / grouped["total_ar_usd"] * 100).round(1),
            0.0
        )
        grouped = grouped[grouped["salesperson_name"] != "No Asignado"]
        grouped.sort_values(by="total_ar_usd", ascending=False, inplace=True)
        return grouped.to_dict(orient="records")

    def get_customers_ar_directory(self, territory="ALL", customer_class="ALL", salesperson="ALL", aging_filter="ALL"):
        df = self._apply_filters(self.df_ar, territory, customer_class, salesperson)

        cust_summary = df.groupby(["customer_id", "customer_name", "customer_class_id", "territory_name", "salesperson_name"]).agg(
            total_debt_usd=("balance_usd", "sum"),
            overdue_debt_usd=("balance_usd", lambda x: x[df.loc[x.index, 'overdue_days'] > 0].sum()),
            current_debt_usd=("balance_usd", lambda x: x[df.loc[x.index, 'overdue_days'] <= 0].sum()),
            credit_limit_usd=("credit_limit_usd", "first"),
            docs_count=("doc_number", "count"),
            max_overdue_days=("overdue_days", "max")
        ).reset_index()

        cust_summary["total_debt_usd"] = cust_summary["total_debt_usd"].round(2)
        cust_summary["overdue_debt_usd"] = cust_summary["overdue_debt_usd"].round(2)
        cust_summary["current_debt_usd"] = cust_summary["current_debt_usd"].round(2)
        cust_summary["credit_utilization_pct"] = np.where(
            cust_summary["credit_limit_usd"] > 0,
            (cust_summary["total_debt_usd"] / cust_summary["credit_limit_usd"] * 100).round(1),
            0.0
        )

        def classify_risk(r):
            if r['max_overdue_days'] > 60:
                return "🔴 Riesgo Alto / Moroso"
            elif r['max_overdue_days'] > 0:
                return "🟡 Vencido Moderado"
            else:
                return "🟢 Al Día"

        cust_summary["risk_status"] = cust_summary.apply(classify_risk, axis=1)

        if aging_filter == "OVERDUE":
            cust_summary = cust_summary[cust_summary["overdue_debt_usd"] > 0]
        elif aging_filter == "CURRENT":
            cust_summary = cust_summary[cust_summary["overdue_debt_usd"] <= 0]

        cust_summary.sort_values(by="total_debt_usd", ascending=False, inplace=True)
        return cust_summary.to_dict(orient="records")

    def get_customer_open_invoices(self, customer_id: str):
        df_cust = self.df_ar[self.df_ar["customer_id"] == customer_id].sort_values(by="due_date", ascending=True)
        return df_cust.to_dict(orient="records")

ar_service = ReceivablesAnalyticsService()
