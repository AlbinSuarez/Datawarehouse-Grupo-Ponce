-- =============================================================================
-- Segmentación RFM (Recency, Frequency, Monetary) y LTV de Clientes
-- =============================================================================

with customer_rfm_base as (
    select
        customer_id,
        customer_name,
        customer_class_id,
        territory_id,
        days_since_last_purchase as recency_days,
        total_orders_count as frequency_orders,
        total_net_revenue as monetary_net_revenue,
        historical_ltv_gross_profit,
        average_order_value,
        current_churn_status
    from {{ ref('int_customer_orders_summary') }}
    where total_orders_count > 0
),

rfm_scoring as (
    select
        *,
        ntile(5) over (order by recency_days desc) as r_score, -- 5: Más reciente, 1: Más antiguo
        ntile(5) over (order by frequency_orders asc) as f_score, -- 5: Mayor frecuencia
        ntile(5) over (order by monetary_net_revenue asc) as m_score -- 5: Mayor gasto monetario
    from customer_rfm_base
),

segmented as (
    select
        *,
        case 
            when r_score >= 4 and f_score >= 4 and m_score >= 4 then 'Champions / VIP'
            when r_score >= 3 and f_score >= 3 then 'Loyal Customers'
            when r_score >= 4 and f_score <= 2 then 'Promising / Recent Buyers'
            when r_score <= 2 and f_score >= 4 then 'At Risk / Need Attention'
            when r_score = 1 and f_score = 1 then 'Hibernating / Churned'
            else 'Standard Customers'
        end as customer_rfm_segment
    from rfm_scoring
)

select
    customer_rfm_segment,
    current_churn_status,
    count(distinct customer_id) as total_customers,
    round(avg(recency_days), 1) as avg_recency_days,
    round(avg(frequency_orders), 1) as avg_orders_count,
    round(sum(monetary_net_revenue), 2) as total_revenue_contribution,
    round(avg(historical_ltv_gross_profit), 2) as avg_historical_ltv
from segmented
group by customer_rfm_segment, current_churn_status
order by total_revenue_contribution desc;
