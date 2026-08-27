{{ config(materialized='table') }}

with territories as (
    select * from {{ ref('stg_gp_rm00303_territories') }}
),

final as (
    select
        md5(territory_id) as territory_sk,
        territory_id,
        territory_description,
        manager_full_name,
        country,
        is_inactive
    from territories
)

select * from final
