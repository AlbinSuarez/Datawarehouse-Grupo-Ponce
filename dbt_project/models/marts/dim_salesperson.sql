{{ config(materialized='table') }}

with salespeople as (
    select * from {{ ref('stg_gp_rm00301_salespeople') }}
),

final as (
    select
        md5(salesperson_id) as salesperson_sk,
        salesperson_id,
        employee_id,
        full_name,
        job_title,
        coalesce(territory_id, 'UNKNOWN_TERR') as territory_id,
        coalesce(commission_pct, 0.0000) as commission_pct,
        is_inactive
    from salespeople
)

select * from final
