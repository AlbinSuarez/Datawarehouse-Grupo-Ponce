{{ config(materialized='view') }}

with source as (
    select * from {{ source('dynamics_gp', 'RM00301') }}
),

renamed_and_cleaned as (
    select
        trim(SLPRSNID) as salesperson_id,
        nullif(trim(EMPLOYID), '') as employee_id,
        nullif(trim(VENDORID), '') as vendor_id,
        trim(SLPRSNFN) as first_name,
        nullif(trim(SPRSNSMN), '') as middle_name,
        trim(SPRSNSLN) as last_name,
        trim(concat(trim(SLPRSNFN), ' ', coalesce(trim(SPRSNSLN), ''))) as full_name,
        nullif(trim(SPRNSTTL), '') as job_title,
        nullif(trim(SALSTERR), '') as territory_id,
        cast(COMPRCNT as numeric(8, 4)) / 100.0 as commission_pct,
        cast(INACTIVE as integer) as is_inactive
    from source
    where SLPRSNID is not null and trim(SLPRSNID) != ''
)

select * from renamed_and_cleaned
