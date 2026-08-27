{{ config(materialized='view') }}

with source as (
    select * from {{ source('dynamics_gp', 'RM00201') }}
),

renamed_and_cleaned as (
    select
        trim(CLASSID) as customer_class_id,
        trim(CLASDSCR) as customer_class_description,
        cast(CRLMTTYP as integer) as default_credit_limit_type,
        cast(CRLMTAMT as numeric(19, 2)) as default_credit_limit_amount,
        nullif(trim(CHEKBKID), '') as default_checkbook_id,
        nullif(trim(PYMTRMID), '') as default_payment_terms_id,
        nullif(trim(PRCLEVEL), '') as default_price_level
    from source
    where CLASSID is not null and trim(CLASSID) != ''
)

select * from renamed_and_cleaned
