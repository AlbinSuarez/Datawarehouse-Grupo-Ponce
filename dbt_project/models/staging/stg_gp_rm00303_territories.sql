{{ config(materialized='view') }}

with source as (
    select * from {{ source('dynamics_gp', 'RM00303') }}
),

renamed_and_cleaned as (
    select
        trim(SALSTERR) as territory_id,
        trim(SLTERDSC) as territory_description,
        nullif(trim(SLPRSNID), '') as manager_salesperson_id,
        nullif(trim(STMGRFNM), '') as manager_first_name,
        nullif(trim(STMGRLNM), '') as manager_last_name,
        trim(concat(coalesce(trim(STMGRFNM), ''), ' ', coalesce(trim(STMGRLNM), ''))) as manager_full_name,
        nullif(trim(COUNTRY), '') as country,
        cast(INACTIVE as integer) as is_inactive
    from source
    where SALSTERR is not null and trim(SALSTERR) != ''
)

select * from renamed_and_cleaned
