{{ config(materialized='table') }}

with items as (
    select * from {{ ref('stg_gp_iv00101_items') }}
),

final as (
    select
        md5(item_number) as product_sk,
        item_number,
        item_description,
        coalesce(item_class_code, 'UNASSIGNED') as item_class_code,
        coalesce(item_generic_description, 'General') as item_generic_desc,
        coalesce(standard_cost, 0.0000) as standard_cost,
        coalesce(current_cost, 0.0000) as current_cost,
        uom_schedule,
        coalesce(decimal_places_qty, 2) as decimal_places_qty,
        coalesce(decimal_places_curr, 2) as decimal_places_curr,
        case when is_inactive = 1 then 0 else 1 end as is_active
    from items
)

select * from final
