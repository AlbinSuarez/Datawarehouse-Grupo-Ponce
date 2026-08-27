{{ config(materialized='table') }}

with sales as (
    select * from {{ ref('int_sales_lines_enriched') }}
),

customers as (
    select * from {{ ref('stg_gp_rm00101_customers') }}
),

-- Generar meses de actividad por cliente
monthly_customer_sales as (
    select
        customer_id,
        date_trunc('month', document_date) as period_month,
        count(distinct case when sop_type = 3 then invoice_number end) as total_invoices_month,
        count(distinct case when sop_type = 4 then invoice_number end) as total_returns_month,
        sum(gross_sales_amount) as gross_sales_month,
        sum(case when sop_type = 4 then abs(gross_sales_amount) else 0 end) as returns_amount_month,
        sum(net_sales_amount) as net_sales_month,
        sum(total_cost_amount) as total_cogs_month,
        sum(gross_profit_amount) as gross_profit_month,
        max(document_date) as last_purchase_date_month
    from sales
    group by 1, 2
),

first_dates as (
    select
        customer_id,
        min(period_month) as cohort_month,
        min(document_date) as first_purchase_date
    from sales
    group by 1
),

-- Ventana acumulada histórica
cumulative_metrics as (
    select
        m.customer_id,
        m.period_month,
        cast(strftime(m.period_month, '%Y%m01') as integer) as year_month_sk,
        f.cohort_month,
        f.first_purchase_date,
        m.total_invoices_month,
        m.total_returns_month,
        m.gross_sales_month,
        m.returns_amount_month,
        m.net_sales_month,
        m.total_cogs_month,
        m.gross_profit_month,
        m.last_purchase_date_month,

        -- Acumulados LTV hasta el mes M
        sum(m.net_sales_month) over (
            partition by m.customer_id 
            order by m.period_month 
            rows between unbounded preceding and current row
        ) as cumulative_net_sales_ltv,

        sum(m.gross_profit_month) over (
            partition by m.customer_id 
            order by m.period_month 
            rows between unbounded preceding and current row
        ) as cumulative_gross_profit_ltv,

        max(m.last_purchase_date_month) over (
            partition by m.customer_id 
            order by m.period_month 
            rows between unbounded preceding and current row
        ) as cumulative_last_purchase_date

    from monthly_customer_sales m
    inner join first_dates f on m.customer_id = f.customer_id
),

final as (
    select
        c.customer_id,
        c.period_month,
        c.year_month_sk,
        c.cohort_month,
        c.first_purchase_date,
        c.total_invoices_month,
        c.total_returns_month,
        c.gross_sales_month,
        c.returns_amount_month,
        c.net_sales_month,
        c.total_cogs_month,
        c.gross_profit_month,
        c.cumulative_net_sales_ltv,
        c.cumulative_gross_profit_ltv,
        c.cumulative_last_purchase_date,

        -- Días desde última compra a fin del mes evaluado
        datediff('day', c.cumulative_last_purchase_date, (c.period_month + interval '1 month - 1 day')::date) as days_since_last_purchase_at_month_end,

        -- Flags de Negocio
        case when c.total_invoices_month > 0 then 1 else 0 end as active_month_flag,
        case when c.period_month = c.cohort_month then 1 else 0 end as is_new_customer_flag,
        case 
            when datediff('day', c.cumulative_last_purchase_date, (c.period_month + interval '1 month - 1 day')::date) > 90 
            then 1 else 0 
        end as is_churned_flag

    from cumulative_metrics c
)

select * from final
