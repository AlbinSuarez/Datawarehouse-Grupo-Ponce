{{ config(materialized='view') }}

with source as (
    select * from {{ source('dynamics_system', 'MC00100') }}
    where trim(EXGTBLID) = 'USD-VENTAS'
      and XCHGRATE > 0
),

renamed as (
    select
        trim(EXGTBLID) as exchange_table_id,
        trim(CURNCYID) as currency_id,
        cast(EXCHDATE as date) as exchange_date,
        cast(XCHGRATE as numeric(19, 7)) as exchange_rate,
        cast(EXPNDATE as date) as expiration_date
    from source
)

select * from renamed
