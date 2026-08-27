-- =============================================================================
-- Análisis de Cohortes de Retención y Churn de Clientes
-- =============================================================================

with cohorts as (
    select
        customer_id,
        date_trunc('month', first_purchase_date) as cohort_month,
        period_month,
        datediff('month', cohort_month, period_month) as month_number,
        active_month_flag,
        net_sales_month,
        cumulative_gross_profit_ltv
    from {{ ref('int_customer_churn_ltv_monthly') }}
)

select
    cohort_month,
    month_number,
    count(distinct customer_id) as total_customers_in_cohort,
    sum(active_month_flag) as active_customers,
    round(sum(active_month_flag) * 100.0 / nullif(count(distinct customer_id), 0), 2) as retention_rate_pct,
    round(100.0 - (sum(active_month_flag) * 100.0 / nullif(count(distinct customer_id), 0)), 2) as churn_rate_pct,
    sum(net_sales_month) as total_cohort_net_sales,
    avg(cumulative_gross_profit_ltv) as average_ltv_gross_profit
from cohorts
group by cohort_month, month_number
order by cohort_month, month_number;
