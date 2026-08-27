"""
Servicio Analítico para el Data Mart de Clientes y Ventas
Calcula KPIs, Churn, LTV, RFM, Cohortes y filtros dinámicos
Utilizando los nombres y asociaciones reales de RM00301 y RM00303
"""

from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from db import db_engine

def apply_filters(df, territory=None, customer_class=None, salesperson=None, start_date=None, end_date=None):
    filtered = df.copy()
    if territory and territory != "ALL":
        filtered = filtered[filtered["territory_name"] == territory]
    if customer_class and customer_class != "ALL":
        filtered = filtered[filtered["customer_class_id"] == customer_class]
    if salesperson and salesperson != "ALL":
        filtered = filtered[filtered["salesperson_name"] == salesperson]
    if start_date:
        filtered = filtered[filtered["document_date"] >= pd.to_datetime(start_date)]
    if end_date:
        filtered = filtered[filtered["document_date"] <= pd.to_datetime(end_date)]
    return filtered

def get_kpis_summary(territory=None, customer_class=None, salesperson=None, start_date=None, end_date=None):
    df_sales = apply_filters(db_engine.fact_sales, territory, customer_class, salesperson, start_date, end_date)
    df_cust = db_engine.dim_customer.copy()
    
    if territory and territory != "ALL":
        df_cust = df_cust[df_cust["territory_name"] == territory]
    if customer_class and customer_class != "ALL":
        df_cust = df_cust[df_cust["customer_class_id"] == customer_class]
    if salesperson and salesperson != "ALL":
        df_cust = df_cust[df_cust["salesperson_name"] == salesperson]

    total_net_sales = float(df_sales["net_sales_amount"].sum())
    total_gross_profit = float(df_sales["gross_profit_amount"].sum())
    gross_margin_pct = round((total_gross_profit / total_net_sales * 100), 2) if total_net_sales > 0 else 0.0
    total_orders = int(df_sales["invoice_number"].nunique())
    total_units = float(df_sales["quantity"].sum())
    aov = round(total_net_sales / total_orders, 2) if total_orders > 0 else 0.0

    # Lógica de Churn & Actividad
    now = datetime.now()
    cutoff_churn = now - timedelta(days=90)
    
    cust_last_purchase = df_sales.groupby("customer_id")["document_date"].max()
    active_customers = int((cust_last_purchase >= cutoff_churn).sum())
    churned_customers = int((cust_last_purchase < cutoff_churn).sum())
    total_active_base = active_customers + churned_customers
    
    churn_rate_pct = round((churned_customers / total_active_base * 100), 2) if total_active_base > 0 else 0.0
    avg_ltv = round(total_gross_profit / total_active_base, 2) if total_active_base > 0 else 0.0

    return {
        "total_net_sales": total_net_sales,
        "total_gross_profit": total_gross_profit,
        "gross_margin_pct": gross_margin_pct,
        "total_orders": total_orders,
        "total_units": total_units,
        "average_order_value": aov,
        "active_customers": active_customers,
        "churned_customers": churned_customers,
        "churn_rate_pct": churn_rate_pct,
        "average_ltv_gross_profit": avg_ltv,
        "total_customers_in_scope": len(df_cust),
        "net_sales": total_net_sales,
        "gross_profit": total_gross_profit,
        "churned_customers_count": churned_customers,
        "average_customer_ltv": avg_ltv
    }

def get_sales_trend(territory=None, customer_class=None, salesperson=None, start_date=None, end_date=None):
    df_sales = apply_filters(db_engine.fact_sales, territory, customer_class, salesperson, start_date, end_date)
    
    monthly = df_sales.groupby("year_month").agg(
        net_sales=("net_sales_amount", "sum"),
        gross_profit=("gross_profit_amount", "sum"),
        orders_count=("invoice_number", "nunique")
    ).reset_index()

    monthly["net_sales"] = monthly["net_sales"].round(2)
    monthly["gross_profit"] = monthly["gross_profit"].round(2)
    monthly["gross_margin_pct"] = np.where(monthly["net_sales"] > 0, (monthly["gross_profit"] / monthly["net_sales"] * 100).round(2), 0.0)
    monthly["month"] = monthly["year_month"]
    monthly["sales"] = monthly["net_sales"]

    return monthly.to_dict(orient="records")

def get_sales_by_territory(territory=None, customer_class=None, salesperson=None, start_date=None, end_date=None):
    df_sales = apply_filters(db_engine.fact_sales, territory, customer_class, salesperson, start_date, end_date)
    grouped = df_sales.groupby("territory_name").agg(
        net_sales=("net_sales_amount", "sum"),
        gross_profit=("gross_profit_amount", "sum"),
        orders_count=("invoice_number", "nunique")
    ).reset_index()
    grouped["net_sales"] = grouped["net_sales"].round(2)
    grouped["gross_profit"] = grouped["gross_profit"].round(2)
    grouped["sales"] = grouped["net_sales"]
    grouped.sort_values(by="net_sales", ascending=False, inplace=True)
    return grouped.to_dict(orient="records")

def get_sales_by_category(territory=None, customer_class=None, salesperson=None, start_date=None, end_date=None):
    df_sales = apply_filters(db_engine.fact_sales, territory, customer_class, salesperson, start_date, end_date)
    grouped = df_sales.groupby("category").agg(
        net_sales=("net_sales_amount", "sum"),
        units_sold=("quantity", "sum")
    ).reset_index()
    grouped["net_sales"] = grouped["net_sales"].round(2)
    grouped["category_id"] = grouped["category"]
    grouped["sales"] = grouped["net_sales"]
    grouped.sort_values(by="net_sales", ascending=False, inplace=True)
    return grouped.to_dict(orient="records")

def get_churn_analysis(territory=None, customer_class=None, salesperson=None):
    df_sales = apply_filters(db_engine.fact_sales, territory, customer_class, salesperson)
    
    # Calcular Churn mensual evolutivo
    monthly_churn = []
    months = sorted(df_sales["year_month"].unique())
    
    for ym in months:
        target_date = datetime.strptime(ym, "%Y-%m") + timedelta(days=28)
        cutoff_date = target_date - timedelta(days=90)
        
        sales_up_to_m = df_sales[df_sales["document_date"] <= target_date]
        cust_last = sales_up_to_m.groupby("customer_id")["document_date"].max()
        
        active = int((cust_last >= cutoff_date).sum())
        churned = int((cust_last < cutoff_date).sum())
        total = active + churned
        rate = round((churned / total * 100), 2) if total > 0 else 0.0
        
        monthly_churn.append({
            "year_month": ym,
            "period": ym,
            "active_customers": active,
            "churned_customers": churned,
            "churn_rate_pct": rate
        })

    # Cohortes de Retención
    cohort_df = df_sales.groupby("customer_id")["document_date"].min().reset_index()
    cohort_df["cohort_month"] = cohort_df["document_date"].dt.strftime("%Y-%m")
    
    df_with_cohort = df_sales.merge(cohort_df[["customer_id", "cohort_month"]], on="customer_id")
    cohort_matrix = []
    
    recent_cohorts = sorted(df_with_cohort["cohort_month"].unique())[-6:]
    for c_month in recent_cohorts:
        c_sales = df_with_cohort[df_with_cohort["cohort_month"] == c_month]
        total_cohort_users = c_sales["customer_id"].nunique()
        
        month_indices = sorted(df_sales["year_month"].unique())
        if c_month in month_indices:
            c_start_idx = month_indices.index(c_month)
            
            retention_row = {
                "cohort_month": c_month,
                "total_users": total_cohort_users,
                "new_customers": total_cohort_users,
                "periods": [],
                "m0": 100.0, "m1": 0.0, "m2": 0.0, "m3": 0.0, "m4": 0.0, "m5": 0.0
            }
            for period_num, ym in enumerate(month_indices[c_start_idx:c_start_idx+6]):
                active_in_period = c_sales[c_sales["year_month"] == ym]["customer_id"].nunique()
                retention_pct = round((active_in_period / total_cohort_users * 100), 1) if total_cohort_users > 0 else 0.0
                retention_row["periods"].append({"period": f"M+{period_num}", "retention_pct": retention_pct, "active_users": active_in_period})
                retention_row[f"m{period_num}"] = retention_pct
            cohort_matrix.append(retention_row)

    return {
        "monthly_trend": monthly_churn,
        "churn_history": monthly_churn,
        "cohort_matrix": cohort_matrix
    }

def get_rfm_and_ltv_customers(territory=None, customer_class=None, salesperson=None):
    df_sales = apply_filters(db_engine.fact_sales, territory, customer_class, salesperson)
    now = datetime.now()
    
    cust_metrics = df_sales.groupby(["customer_id", "customer_name", "customer_class_id", "territory_name", "salesperson_name"]).agg(
        last_purchase=("document_date", "max"),
        first_purchase=("document_date", "min"),
        frequency=("invoice_number", "nunique"),
        monetary=("net_sales_amount", "sum"),
        gross_profit_ltv=("gross_profit_amount", "sum")
    ).reset_index()

    cust_metrics["recency_days"] = (now - cust_metrics["last_purchase"]).dt.days
    cust_metrics["tenure_days"] = (now - cust_metrics["first_purchase"]).dt.days
    cust_metrics["monetary"] = cust_metrics["monetary"].round(2)
    cust_metrics["gross_profit_ltv"] = cust_metrics["gross_profit_ltv"].round(2)
    cust_metrics["average_order_value"] = (cust_metrics["monetary"] / cust_metrics["frequency"]).round(2)
    cust_metrics["total_orders"] = cust_metrics["frequency"]
    cust_metrics["total_net_sales"] = cust_metrics["monetary"]
    cust_metrics["customer_ltv_gross_profit"] = cust_metrics["gross_profit_ltv"]

    # Segmentación RFM
    r_med = cust_metrics["recency_days"].median()
    f_med = cust_metrics["frequency"].median()
    m_med = cust_metrics["monetary"].median()

    def classify_rfm(row):
        if row["recency_days"] <= 60 and row["frequency"] >= f_med and row["monetary"] >= m_med:
            return "Campeones / VIP"
        elif row["recency_days"] <= 90 and row["frequency"] >= f_med:
            return "Leales Potenciales"
        elif row["recency_days"] <= 45 and row["frequency"] < f_med:
            return "Prometedores / Recientes"
        elif row["recency_days"] > 90 and row["monetary"] >= m_med:
            return "En Riesgo"
        elif row["recency_days"] > 90:
            return "Inactivos / Perdidos"
        else:
            return "Estándar"

    cust_metrics["segment"] = cust_metrics.apply(classify_rfm, axis=1)
    cust_metrics["rfm_segment"] = cust_metrics["segment"]

    # Resumen por segmento
    segment_summary = cust_metrics.groupby("segment").agg(
        customer_count=("customer_id", "count"),
        total_revenue=("monetary", "sum"),
        avg_ltv=("gross_profit_ltv", "mean"),
        avg_recency=("recency_days", "mean")
    ).reset_index()

    segment_summary["total_revenue"] = segment_summary["total_revenue"].round(2)
    segment_summary["total_sales"] = segment_summary["total_revenue"]
    segment_summary["avg_ltv"] = segment_summary["avg_ltv"].round(2)
    segment_summary["avg_recency"] = segment_summary["avg_recency"].round(1)
    segment_summary["avg_recency_days"] = segment_summary["avg_recency"]

    top_ltv = cust_metrics.sort_values(by="gross_profit_ltv", ascending=False).head(20)
    all_cust = cust_metrics.sort_values(by="gross_profit_ltv", ascending=False)

    return {
        "segment_summary": segment_summary.to_dict(orient="records"),
        "rfm_summary": segment_summary.to_dict(orient="records"),
        "top_ltv_customers": top_ltv.to_dict(orient="records"),
        "all_customers_rfm": all_cust.to_dict(orient="records"),
        "customers": all_cust.to_dict(orient="records")
    }
