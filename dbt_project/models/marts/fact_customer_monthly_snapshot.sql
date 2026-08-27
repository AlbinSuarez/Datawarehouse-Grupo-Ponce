{{ config(materialized='table') }}

with churn_monthly as (
    select * from {{ ref('int_customer_churn_ltv_monthly') }}
),

customers as (
    select * from {{ ref('dim_customer') }}
    where is_current = true
),

salespeople as (
    select * from {{ ref('dim_salesperson') }}
),

territories as (
    select * from {{ ref('dim_territory') }}
),

final as (
    select
        md5(concat(m.customer_id, '_', cast(m.year_month_sk as varchar))) as snapshot_sk,
        m.year_month_sk,
        coalesce(c.customer_sk, md5('UNKNOWN_CUSTOMER')) as customer_sk,
        coalesce(sp.salesperson_sk, md5('UNKNOWN_SP')) as salesperson_sk,
        coalesce(t.territory_sk, md5('UNKNOWN_TERR')) as territory_sk,
        m.customer_id,
        
        -- Flags Analíticos
        m.active_month_flag,
        m.is_churned_flag,
        m.is_new_customer_flag,
        case 
            when m.active_month_flag = 1 and lag(m.is_churned_flag) over (partition by m.customer_id order by m.period_month) = 1
            then 1 else 0 
        end as is_reactivated_flag,

        -- Métricas Mensuales
        m.total_invoices_month,
        m.total_returns_month,
        m.gross_sales_month,
        m.returns_amount_month,
        m.net_sales_month,
        m.total_cogs_month,
        m.gross_profit_month,

        -- Métricas Acumuladas de LTV
        m.cumulative_net_sales_ltv,
        m.cumulative_gross_profit_ltv,
        m.days_since_last_purchase_at_month_end as days_since_last_purchase,
        m.cumulative_last_purchase_date as last_purchase_date

    from churn_monthly m
    left join customers c on m.customer_id = c.customer_id
    left join salespeople sp on c.salesperson_id = sp.salesperson_id
    left join territories t on c.territory_id = t.territory_id
)

select * from final
