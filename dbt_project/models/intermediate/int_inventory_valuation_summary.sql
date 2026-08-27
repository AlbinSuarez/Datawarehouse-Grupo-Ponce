{{ config(materialized='table') }}

with stock as (
    select * from {{ ref('stg_gp_iv00102_item_quantities') }}
    where record_type = 1 -- Total general por artículo
),

items as (
    select * from {{ ref('stg_gp_iv00101_items') }}
),

latest_fx as (
    select top 1 exchange_rate
    from {{ ref('stg_gp_mc00100_exchange_rates') }}
    order by exchange_date desc
),

sales_cogs as (
    select 
        item_number,
        sum(case when document_date >= dateadd(month, -12, current_date) then total_cost_amount else 0 end) as annual_cogs_usd,
        sum(case when document_date >= dateadd(month, -3, current_date) then net_quantity else 0 end) as qty_sold_last_90d
    from {{ ref('int_sales_lines_enriched') }}
    group by item_number
),

joined as (
    select
        s.item_number,
        i.item_description,
        i.item_class_code as category,
        s.qty_on_hand,
        s.qty_allocated,
        s.qty_available,
        s.qty_on_order,
        s.safety_stock_qty,
        s.reorder_point_qty,
        
        -- Costo unitario convertido a USD
        round(coalesce(i.current_cost, i.standard_cost, 0.0) / nullif((select exchange_rate from latest_fx), 0), 4) as unit_cost_usd,
        
        -- Valoración total en USD
        round(s.qty_on_hand * (coalesce(i.current_cost, i.standard_cost, 0.0) / nullif((select exchange_rate from latest_fx), 0)), 2) as total_valuation_usd,
        
        -- COGS anualizado
        coalesce(c.annual_cogs_usd, 0.0) as annual_cogs_usd,
        coalesce(c.qty_sold_last_90d, 0.0) as qty_sold_last_90d,

        -- Rotación de Inventario (Turnover)
        case 
            when (s.qty_on_hand * (coalesce(i.current_cost, i.standard_cost, 0.0) / nullif((select exchange_rate from latest_fx), 0))) > 0
            then round(coalesce(c.annual_cogs_usd, 0.0) / (s.qty_on_hand * (coalesce(i.current_cost, i.standard_cost, 0.0) / nullif((select exchange_rate from latest_fx), 0))), 2)
            else 0.0
        end as inventory_turnover,

        -- Días de Inventario Disponible (DIO)
        case 
            when coalesce(c.annual_cogs_usd, 0.0) > 0
            then round((s.qty_on_hand * (coalesce(i.current_cost, i.standard_cost, 0.0) / nullif((select exchange_rate from latest_fx), 0))) / (c.annual_cogs_usd / 365.0), 1)
            else 999.0 -- Sin ventas recientes / Stock inmovilizado
        end as days_inventory_outstanding,

        -- Semáforo de Salud
        case
            when s.qty_available <= 0 and coalesce(c.qty_sold_last_90d, 0) > 0 then 'Quiebre de Stock (Stockout)'
            when s.qty_available < s.safety_stock_qty or (coalesce(c.annual_cogs_usd, 0) > 0 and (s.qty_on_hand * (coalesce(i.current_cost, i.standard_cost, 0.0) / nullif((select exchange_rate from latest_fx), 0))) / (c.annual_cogs_usd / 365.0) < 15) then 'Riesgo Crítico'
            when (coalesce(c.annual_cogs_usd, 0) > 0 and (s.qty_on_hand * (coalesce(i.current_cost, i.standard_cost, 0.0) / nullif((select exchange_rate from latest_fx), 0))) / (c.annual_cogs_usd / 365.0) > 180) or coalesce(c.annual_cogs_usd, 0) = 0 then 'Sobreinventario'
            else 'Óptimo'
        end as stock_health_status

    from stock s
    left join items i on s.item_number = i.item_number
    left join sales_cogs c on s.item_number = c.item_number
)

select * from joined
