{{ config(materialized='table') }}

with sales as (
    select * from {{ ref('int_sales_lines_enriched') }}
),

customers as (
    select * from {{ ref('stg_gp_rm00101_customers') }}
),

customer_aggregates as (
    select
        customer_id,
        min(document_date) as first_purchase_date,
        max(document_date) as last_purchase_date,
        count(distinct case when sop_type = 3 then invoice_number end) as total_invoices_count,
        count(distinct case when sop_type = 4 then invoice_number end) as total_returns_count,
        count(distinct invoice_number) as total_orders_count,
        sum(gross_sales_amount) as total_gross_revenue,
        sum(case when sop_type = 4 then abs(gross_sales_amount) else 0 end) as total_returns_amount,
        sum(net_sales_amount) as total_net_revenue,
        sum(total_cost_amount) as total_cogs,
        sum(gross_profit_amount) as total_historical_gross_profit,
        sum(net_quantity) as total_units_purchased
    from sales
    group by customer_id
),

final as (
    select
        c.customer_id,
        c.customer_name,
        c.customer_class_id,
        c.salesperson_id,
        c.territory_id,
        c.credit_limit_amount,
        c.is_inactive as is_inactive_in_source,
        coalesce(agg.first_purchase_date, c.created_at::date) as first_purchase_date,
        agg.last_purchase_date,
        coalesce(agg.total_invoices_count, 0) as total_invoices_count,
        coalesce(agg.total_returns_count, 0) as total_returns_count,
        coalesce(agg.total_orders_count, 0) as total_orders_count,
        coalesce(agg.total_gross_revenue, 0) as total_gross_revenue,
        coalesce(agg.total_returns_amount, 0) as total_returns_amount,
        coalesce(agg.total_net_revenue, 0) as total_net_revenue,
        coalesce(agg.total_cogs, 0) as total_cogs,
        coalesce(agg.total_historical_gross_profit, 0) as historical_ltv_gross_profit,
        coalesce(agg.total_units_purchased, 0) as total_units_purchased,
        
        -- Métricas Derivadas
        round(coalesce(agg.total_net_revenue, 0) / nullif(agg.total_orders_count, 0), 2) as average_order_value,
        round(coalesce(agg.total_historical_gross_profit, 0) * 100.0 / nullif(agg.total_net_revenue, 0), 2) as historical_gross_margin_pct,
        
        -- Días desde última compra al día de hoy
        case 
            when agg.last_purchase_date is not null 
            then datediff('day', agg.last_purchase_date, current_date)
            else null 
        end as days_since_last_purchase,

        -- Clasificación actual Churn (>90 días sin compra)
        case 
            when agg.last_purchase_date is null then 'Never Purchased'
            when datediff('day', agg.last_purchase_date, current_date) > 90 then 'Churned / Inactive'
            else 'Active'
        end as current_churn_status

    from customers c
    left join customer_aggregates agg
        on c.customer_id = agg.customer_id
)

select * from final
