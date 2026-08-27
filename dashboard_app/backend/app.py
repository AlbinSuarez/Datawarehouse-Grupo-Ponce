"""
Servidor Backend FastAPI para el Dashboard Web Dinámico
Módulos: Ventas, Clientes, Churn, LTV, Inventarios y Cuentas por Cobrar (AR)
"""

import os
import asyncio
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import analytics_service
from analytics_inventory_service import inv_service
from analytics_receivables_service import ar_service
from db import db_engine

app = FastAPI(title="Grupo Ponce - Data Mart Clientes, Ventas, Inventarios & Cobranzas API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def start_periodic_sync():
    async def periodic_refresh():
        while True:
            # Intervalo de 4 horas (14,400 segundos)
            await asyncio.sleep(4 * 3600)
            try:
                print("\n[AUTO-SYNC] Ejecutando sincronización periódica en segundo plano (cada 4h)...")
                db_engine.load_real_datamart()
                inv_service._load_inventory_data()
                ar_service._load_ar_data()
                print("[AUTO-SYNC] Datos actualizados en memoria exitosamente.\n")
            except Exception as e:
                print(f"[AUTO-SYNC ERROR] Error en sincronización: {e}\n")

    asyncio.create_task(periodic_refresh())

frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(frontend_dir, "index.html"))

@app.post("/api/meta/reload")
@app.get("/api/meta/reload")
def reload_all_data():
    db_engine.load_real_datamart()
    inv_service._load_inventory_data()
    ar_service._load_ar_data()
    return {
        "status": "success",
        "latest_rate": db_engine.latest_rate,
        "latest_rate_date": db_engine.latest_rate_date,
        "total_sales_rows": len(db_engine.fact_sales),
        "total_inventory_items": len(inv_service.df_inventory),
        "total_ar_documents": len(ar_service.df_ar)
    }

@app.get("/api/meta/filters")
def get_filter_options():
    territories = sorted([t for t in db_engine.fact_sales["territory_name"].dropna().unique().tolist() if t and t not in ('INACTIVO', 'Sin Zona')])
    classes = sorted([c for c in db_engine.fact_sales["customer_class_id"].dropna().unique().tolist() if c])
    salespeople = sorted([s for s in db_engine.fact_sales["salesperson_name"].dropna().unique().tolist() if s and s != 'No Asignado' and 'INACTIVO' not in s])
    
    inv_categories = sorted([c for c in inv_service.df_inventory["category"].dropna().unique().tolist() if c])
    min_date = db_engine.fact_sales["document_date"].min().strftime("%Y-%m-%d")
    max_date = db_engine.fact_sales["document_date"].max().strftime("%Y-%m-%d")

    # Mapeo de Vendedores por Territorio / Zona
    fs_sp = db_engine.fact_sales[
        (db_engine.fact_sales["territory_name"].notna()) &
        (db_engine.fact_sales["salesperson_name"].notna()) &
        (db_engine.fact_sales["salesperson_name"] != 'No Asignado') &
        (~db_engine.fact_sales["salesperson_name"].str.contains('INACTIVO'))
    ][["territory_name", "salesperson_name"]].drop_duplicates()

    sp_by_terr = {}
    for _, row in fs_sp.iterrows():
        t = row["territory_name"]
        s = row["salesperson_name"]
        if t not in sp_by_terr:
            sp_by_terr[t] = []
        if s not in sp_by_terr[t]:
            sp_by_terr[t].append(s)

    for k in sp_by_terr:
        sp_by_terr[k] = sorted(sp_by_terr[k])

    return {
        "territories": territories,
        "customer_classes": classes,
        "salespeople": salespeople,
        "salespeople_by_territory": sp_by_terr,
        "inventory_categories": inv_categories,
        "min_date": min_date,
        "max_date": max_date,
        "latest_rate": db_engine.latest_rate,
        "latest_rate_date": db_engine.latest_rate_date,
        "exchange_table": "USD-VENTAS (MC00100)",
        "database_target": f"{db_engine.server}: {db_engine.db_name} + {db_engine.dyn_db} (SQL Server)"
    }

# =========================================================================
# RUTAS DE VENTAS & CLIENTES
# =========================================================================
@app.get("/api/kpis/summary")
def get_kpis(
    territory: str = Query("ALL"),
    customer_class: str = Query("ALL"),
    salesperson: str = Query("ALL"),
    start_date: str = Query(None),
    end_date: str = Query(None)
):
    return analytics_service.get_kpis_summary(territory, customer_class, salesperson, start_date, end_date)

@app.get("/api/sales/trends")
def get_sales_trend(
    territory: str = Query("ALL"),
    customer_class: str = Query("ALL"),
    salesperson: str = Query("ALL"),
    start_date: str = Query(None),
    end_date: str = Query(None)
):
    return analytics_service.get_sales_trend(territory, customer_class, salesperson, start_date, end_date)

@app.get("/api/sales/by-territory")
def get_sales_territory(
    territory: str = Query("ALL"),
    customer_class: str = Query("ALL"),
    salesperson: str = Query("ALL"),
    start_date: str = Query(None),
    end_date: str = Query(None)
):
    return analytics_service.get_sales_by_territory(territory, customer_class, salesperson, start_date, end_date)

@app.get("/api/sales/by-category")
def get_sales_category(
    territory: str = Query("ALL"),
    customer_class: str = Query("ALL"),
    salesperson: str = Query("ALL"),
    start_date: str = Query(None),
    end_date: str = Query(None)
):
    return analytics_service.get_sales_by_category(territory, customer_class, salesperson, start_date, end_date)

@app.get("/api/churn/analysis")
def get_churn_metrics(
    territory: str = Query("ALL"),
    customer_class: str = Query("ALL"),
    salesperson: str = Query("ALL")
):
    return analytics_service.get_churn_analysis(territory, customer_class, salesperson)

@app.get("/api/customers/rfm-ltv")
def get_rfm_and_ltv(
    territory: str = Query("ALL"),
    customer_class: str = Query("ALL"),
    salesperson: str = Query("ALL")
):
    return analytics_service.get_rfm_and_ltv_customers(territory, customer_class, salesperson)

@app.get("/api/customers/{customer_id}/360")
def get_customer_360(customer_id: str):
    cust = db_engine.dim_customer[db_engine.dim_customer["customer_id"] == customer_id]
    if cust.empty:
        return {"error": "Cliente no encontrado"}
    cust_info = cust.iloc[0].to_dict()
    
    sales = db_engine.fact_sales[db_engine.fact_sales["customer_id"] == customer_id].sort_values(by="document_date", ascending=False).copy()
    
    total_sales = float(sales["net_sales_amount"].sum()) if not sales.empty else 0.0
    total_gp = float(sales["gross_profit_amount"].sum()) if not sales.empty else 0.0
    orders = int(sales["invoice_number"].nunique()) if not sales.empty else 0
    
    if not sales.empty:
        sales["document_type_id"] = sales["sop_type"]
        sales["item_id"] = sales["item_number"]
        sales["document_date"] = sales["document_date"].dt.strftime("%Y-%m-%d")
    
    return {
        "profile": cust_info,
        "metrics": {
            "total_sales": total_sales,
            "total_gross_profit": total_gp,
            "total_orders": orders,
            "average_order_value": round(total_sales / orders, 2) if orders > 0 else 0
        },
        "recent_transactions": sales.head(15).to_dict(orient="records") if not sales.empty else []
    }

# =========================================================================
# RUTAS DE INVENTARIOS & STOCK
# =========================================================================
@app.get("/api/inventory/kpis")
def get_inv_kpis(sku_type: str = Query("ALL"), category: str = Query("ALL")):
    return inv_service.get_inventory_kpis(sku_type, category)

@app.get("/api/inventory/by-category")
def get_inv_by_category(sku_type: str = Query("ALL")):
    return inv_service.get_inventory_by_category(sku_type)

@app.get("/api/inventory/by-location")
def get_inv_by_location(sku_type: str = Query("ALL")):
    return inv_service.get_inventory_by_location(sku_type)

@app.get("/api/inventory/health-summary")
def get_inv_health_summary(sku_type: str = Query("ALL"), category: str = Query("ALL")):
    return inv_service.get_health_summary(sku_type, category)

@app.get("/api/inventory/items")
def get_inv_items(sku_type: str = Query("ALL"), category: str = Query("ALL"), health_status: str = Query("ALL")):
    return inv_service.get_items_directory(sku_type, category, health_status)

# =========================================================================
# RUTAS DE CUENTAS POR COBRAR (RECEIVABLES / AR)
# =========================================================================
@app.get("/api/ar/kpis")
def get_ar_kpis(
    territory: str = Query("ALL"),
    customer_class: str = Query("ALL"),
    salesperson: str = Query("ALL")
):
    return ar_service.get_ar_kpis(territory, customer_class, salesperson)

@app.get("/api/ar/aging-summary")
def get_ar_aging_summary(
    territory: str = Query("ALL"),
    customer_class: str = Query("ALL"),
    salesperson: str = Query("ALL")
):
    return ar_service.get_aging_summary(territory, customer_class, salesperson)

@app.get("/api/ar/by-territory")
def get_ar_by_territory():
    return ar_service.get_ar_by_territory()

@app.get("/api/ar/by-salesperson")
def get_ar_by_salesperson():
    return ar_service.get_ar_by_salesperson()

@app.get("/api/ar/customers")
def get_ar_customers(
    territory: str = Query("ALL"),
    customer_class: str = Query("ALL"),
    salesperson: str = Query("ALL"),
    aging_filter: str = Query("ALL")
):
    return ar_service.get_customers_ar_directory(territory, customer_class, salesperson, aging_filter)

@app.get("/api/ar/customer/{customer_id}/invoices")
def get_ar_customer_invoices(customer_id: str):
    return ar_service.get_customer_open_invoices(customer_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
