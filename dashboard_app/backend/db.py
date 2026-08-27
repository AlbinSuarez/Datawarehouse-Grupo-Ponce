"""
Capa de Conexión a Base de Datos y Datos Analíticos REALES
Servidor: localhost (Microsoft SQL Server)
Bases de Datos: PB (Transaccional) y DYNAMICS (Tasas Cambiarias MC00100)
"""

import os
import pyodbc
import pandas as pd
import numpy as np
from datetime import datetime

class RealDataMartEngine:
    def __init__(self):
        self.server = os.getenv("DB_HOST", "localhost")
        self.user = os.getenv("DB_USER", "sa")
        self.password = os.getenv("DB_PASSWORD", "Br4s1l")
        self.db_name = os.getenv("DB_NAME", "PB")
        self.dyn_db = os.getenv("DYN_DB", "DYNAMICS")
        
        self.dim_customer = pd.DataFrame()
        self.dim_product = pd.DataFrame()
        self.dim_salesperson = pd.DataFrame()
        self.dim_territory = pd.DataFrame()
        self.dim_exchange_rate = pd.DataFrame()
        self.fact_sales = pd.DataFrame()
        
        self.latest_rate = 1.0
        self.latest_rate_date = ""
        self.is_connected = False
        self.load_real_datamart()

    def get_connection(self):
        conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={self.server};UID={self.user};PWD={self.password};TrustServerCertificate=yes;"
        return pyodbc.connect(conn_str, timeout=10)

    def load_real_datamart(self):
        print(f"=================================================================")
        print(f" CONECTANDO AL SERVIDOR SQL SERVER EN: {self.server}")
        print(f" Bases de Datos: {self.db_name} y {self.dyn_db}")
        print(f"=================================================================")
        
        try:
            conn = self.get_connection()
            self.is_connected = True
            
            # 1. Cargar Tasas Cambiarias (DYNAMICS.dbo.MC00100 - USD-VENTAS)
            print("1. Extrayendo tasas cambiarias de DYNAMICS.dbo.MC00100 (USD-VENTAS)...")
            fx_query = """
                SELECT 
                    CAST(EXCHDATE AS DATE) AS exch_date,
                    CAST(XCHGRATE AS FLOAT) AS xchg_rate
                FROM DYNAMICS.dbo.MC00100
                WHERE EXGTBLID = 'USD-VENTAS' AND XCHGRATE > 0
                ORDER BY EXCHDATE ASC
            """
            df_fx = pd.read_sql(fx_query, conn)
            df_fx = df_fx.drop_duplicates(subset=["exch_date"], keep="last")
            df_fx.sort_values(by="exch_date", inplace=True)
            self.dim_exchange_rate = df_fx
            
            if not df_fx.empty:
                last_row = df_fx.iloc[-1]
                self.latest_rate = float(last_row["xchg_rate"])
                self.latest_rate_date = str(last_row["exch_date"])
                print(f"   -> Tasa del Día USD-VENTAS: {self.latest_rate:.4f} VEF/USD (al {self.latest_rate_date})")

            # 2. Cargar Territorios / Zonas (PB.dbo.RM00303)
            print("2. Extrayendo Zonas / Territorios de PB.dbo.RM00303...")
            terr_query = """
                SELECT 
                    RTRIM(SALSTERR) AS territory_id,
                    RTRIM(SLTERDSC) AS territory_name,
                    RTRIM(STMGRFNM) + ' ' + RTRIM(STMGRLNM) AS manager_name,
                    CAST(INACTIVE AS INT) AS is_inactive
                FROM PB.dbo.RM00303
            """
            self.dim_territory = pd.read_sql(terr_query, conn)

            # 3. Cargar Vendedores (PB.dbo.RM00301)
            print("3. Extrayendo Vendedores de PB.dbo.RM00301...")
            sp_query = """
                SELECT 
                    RTRIM(sp.SLPRSNID) AS salesperson_id,
                    RTRIM(sp.SLPRSNFN) AS first_name,
                    RTRIM(sp.SPRSNSLN) AS last_name,
                    LTRIM(RTRIM(RTRIM(sp.SLPRSNFN) + ' ' + RTRIM(sp.SPRSNSLN))) AS salesperson_name,
                    '[' + RTRIM(sp.SLPRSNID) + '] ' + LTRIM(RTRIM(RTRIM(sp.SLPRSNFN) + ' ' + RTRIM(sp.SPRSNSLN))) AS salesperson_display,
                    RTRIM(sp.SALSTERR) AS territory_id,
                    COALESCE(RTRIM(t.SLTERDSC), 'Sin Zona Asignada') AS territory_name,
                    CAST(sp.INACTIVE AS INT) AS is_inactive
                FROM PB.dbo.RM00301 sp
                LEFT JOIN PB.dbo.RM00303 t ON sp.SALSTERR = t.SALSTERR
            """
            self.dim_salesperson = pd.read_sql(sp_query, conn)

            # 4. Cargar Clientes (PB.dbo.RM00101)
            print("4. Extrayendo Clientes de PB.dbo.RM00101...")
            cust_query = """
                SELECT 
                    RTRIM(c.CUSTNMBR) AS customer_id,
                    RTRIM(c.CUSTNAME) AS customer_name,
                    COALESCE(NULLIF(RTRIM(c.CUSTCLAS), ''), 'GENERAL') AS customer_class_id,
                    COALESCE(NULLIF(RTRIM(c.SLPRSNID), ''), 'SIN_VENDEDOR') AS salesperson_id,
                    COALESCE(NULLIF(LTRIM(RTRIM(RTRIM(sp.SLPRSNFN) + ' ' + RTRIM(sp.SPRSNSLN))), ''), RTRIM(c.SLPRSNID), 'No Asignado') AS salesperson_name,
                    COALESCE(NULLIF(RTRIM(t.SLTERDSC), ''), NULLIF(RTRIM(t_sp.SLTERDSC), ''), RTRIM(c.SALSTERR), 'Sin Zona') AS territory_name,
                    COALESCE(NULLIF(RTRIM(c.SALSTERR), ''), RTRIM(sp.SALSTERR), '0') AS territory_id,
                    CAST(c.CRLMTAMT AS FLOAT) AS credit_limit,
                    CAST(c.CREATDDT AS DATE) AS created_at,
                    RTRIM(c.PHONE1) AS phone,
                    RTRIM(c.CITY) AS city,
                    CAST(c.INACTIVE AS INT) AS is_inactive_source
                FROM PB.dbo.RM00101 c
                LEFT JOIN PB.dbo.RM00301 sp ON c.SLPRSNID = sp.SLPRSNID
                LEFT JOIN PB.dbo.RM00303 t ON c.SALSTERR = t.SALSTERR
                LEFT JOIN PB.dbo.RM00303 t_sp ON sp.SALSTERR = t_sp.SALSTERR
            """
            self.dim_customer = pd.read_sql(cust_query, conn)

            # 5. Cargar Artículos (PB.dbo.IV00101)
            print("5. Extrayendo Artículos de PB.dbo.IV00101...")
            item_query = """
                SELECT 
                    RTRIM(ITEMNMBR) AS item_number,
                    RTRIM(ITEMDESC) AS item_description,
                    COALESCE(NULLIF(RTRIM(ITMCLSCD), ''), 'GENERAL') AS category,
                    CAST(STNDCOST AS FLOAT) AS standard_cost,
                    CAST(CURRCOST AS FLOAT) AS current_cost
                FROM PB.dbo.IV00101
            """
            self.dim_product = pd.read_sql(item_query, conn)

            # 6. Cargar Ventas (SOP30200 + SOP30300)
            print("6. Extrayendo y asociando ventas (SOP30200 + SOP30300)...")
            sales_query = """
                SELECT 
                    h.SOPTYPE AS sop_type,
                    RTRIM(h.SOPNUMBE) AS invoice_number,
                    l.LNITMSEQ AS line_item_sequence,
                    CAST(h.DOCDATE AS DATE) AS document_date,
                    RTRIM(h.CUSTNMBR) AS customer_id,
                    RTRIM(h.CUSTNAME) AS customer_name,
                    COALESCE(NULLIF(RTRIM(c.CUSTCLAS), ''), 'GENERAL') AS customer_class_id,
                    COALESCE(
                        NULLIF(LTRIM(RTRIM(RTRIM(sp.SLPRSNFN) + ' ' + RTRIM(sp.SPRSNSLN))), ''),
                        NULLIF(LTRIM(RTRIM(RTRIM(sp_cust.SLPRSNFN) + ' ' + RTRIM(sp_cust.SPRSNSLN))), ''),
                        RTRIM(h.SLPRSNID),
                        'No Asignado'
                    ) AS salesperson_name,
                    COALESCE(NULLIF(RTRIM(h.SLPRSNID), ''), RTRIM(c.SLPRSNID), 'SIN_VENDEDOR') AS salesperson_id,
                    COALESCE(
                        NULLIF(RTRIM(t.SLTERDSC), ''),
                        NULLIF(RTRIM(t_sp.SLTERDSC), ''),
                        NULLIF(RTRIM(t_cust.SLTERDSC), ''),
                        RTRIM(h.SALSTERR),
                        'Sin Zona'
                    ) AS territory_name,
                    COALESCE(NULLIF(RTRIM(h.SALSTERR), ''), RTRIM(sp.SALSTERR), RTRIM(c.SALSTERR), '0') AS territory_id,
                    RTRIM(l.ITEMNMBR) AS item_number,
                    RTRIM(l.ITEMDESC) AS item_description,
                    COALESCE(NULLIF(RTRIM(i.ITMCLSCD), ''), 'GENERAL') AS category,
                    RTRIM(h.CURNCYID) AS currency_id,
                    CAST(h.XCHGRATE AS FLOAT) AS header_rate,
                    CAST(l.QUANTITY AS FLOAT) AS quantity,
                    CAST(l.UNITPRCE AS FLOAT) AS unit_price_vef,
                    CAST(l.XTNDPRCE AS FLOAT) AS extended_price_vef,
                    CAST(l.OXTNDPRC AS FLOAT) AS orig_extended_price,
                    CAST(l.UNITCOST AS FLOAT) AS unit_cost_vef,
                    CAST(l.EXTDCOST AS FLOAT) AS extended_cost_vef,
                    CAST(COALESCE(l.MRKDNAMT, 0) AS FLOAT) AS markdown_vef
                FROM PB.dbo.SOP30200 h
                INNER JOIN PB.dbo.SOP30300 l ON h.SOPTYPE = l.SOPTYPE AND h.SOPNUMBE = l.SOPNUMBE
                LEFT JOIN PB.dbo.RM00101 c ON h.CUSTNMBR = c.CUSTNMBR
                LEFT JOIN PB.dbo.RM00301 sp ON h.SLPRSNID = sp.SLPRSNID
                LEFT JOIN PB.dbo.RM00301 sp_cust ON c.SLPRSNID = sp_cust.SLPRSNID
                LEFT JOIN PB.dbo.RM00303 t ON h.SALSTERR = t.SALSTERR
                LEFT JOIN PB.dbo.RM00303 t_sp ON sp.SALSTERR = t_sp.SALSTERR
                LEFT JOIN PB.dbo.RM00303 t_cust ON c.SALSTERR = t_cust.SALSTERR
                LEFT JOIN PB.dbo.IV00101 i ON l.ITEMNMBR = i.ITEMNMBR
                WHERE h.SOPTYPE IN (3, 4) 
                  AND h.VOIDSTTS = 0
                  AND h.DOCDATE >= DATEADD(month, -36, GETDATE())
                ORDER BY h.DOCDATE ASC
            """
            df_sales = pd.read_sql(sales_query, conn)
            conn.close()

            # Conversión a USD
            df_sales['document_date'] = pd.to_datetime(df_sales['document_date'])
            df_fx['exch_date'] = pd.to_datetime(df_fx['exch_date'])
            
            df_sales_sorted = df_sales.sort_values(by='document_date')
            df_merged = pd.merge_asof(
                df_sales_sorted,
                df_fx,
                left_on='document_date',
                right_on='exch_date',
                direction='backward'
            )

            effective_rate = np.where(
                df_merged['header_rate'] > 0,
                df_merged['header_rate'],
                np.where(df_merged['xchg_rate'] > 0, df_merged['xchg_rate'], 1.0)
            )
            df_merged['effective_rate'] = effective_rate

            direction = np.where(df_merged['sop_type'] == 4, -1.0, 1.0)
            df_merged['direction_multiplier'] = direction
            df_merged['doc_type_desc'] = np.where(df_merged['sop_type'] == 4, "Devolución", "Factura")
            df_merged['quantity'] = df_merged['quantity'] * direction

            is_orig_usd = (df_merged['currency_id'].str.strip() == 'USD') & (df_merged['orig_extended_price'] > 0)
            
            net_sales_usd = np.where(
                is_orig_usd,
                df_merged['orig_extended_price'] * direction,
                ((df_merged['extended_price_vef'] - df_merged['markdown_vef']) / df_merged['effective_rate']) * direction
            )
            
            cost_usd = (df_merged['extended_cost_vef'] / df_merged['effective_rate']) * direction
            gross_profit_usd = net_sales_usd - cost_usd

            df_merged['net_sales_amount'] = np.round(net_sales_usd, 2)
            df_merged['extended_cost_usd'] = np.round(cost_usd, 2)
            df_merged['gross_profit_amount'] = np.round(gross_profit_usd, 2)
            df_merged['year_month'] = df_merged['document_date'].dt.strftime('%Y-%m')

            df_merged['territory_name'] = df_merged['territory_name'].str.strip()
            df_merged['salesperson_name'] = df_merged['salesperson_name'].str.strip()

            self.fact_sales = df_merged
            print(f"   -> ETL COMPLETADO: {len(self.fact_sales):,} líneas cargadas.")
            print(f"=================================================================\n")

        except Exception as e:
            print(f"Error al conectar o extraer datos de SQL Server: {e}")

db_engine = RealDataMartEngine()
