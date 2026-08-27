{{ config(materialized='view') }}

with source as (
    select * from {{ source('dynamics_gp', 'SOP30200') }}
),

renamed_and_cleaned as (
    select
        cast(SOPTYPE as integer) as sop_type,
        trim(SOPNUMBE) as invoice_number,
        case cast(SOPTYPE as integer)
            when 1 then 'Quote'
            when 2 then 'Order'
            when 3 then 'Invoice'
            when 4 then 'Return'
            when 5 then 'Backorder'
            when 6 then 'Fulfillment Order'
            else 'Unknown'
        end as document_type_name,
        nullif(trim(DOCID), '') as doc_id,
        cast(DOCDATE as date) as document_date,
        cast(GLPOSTDT as date) as gl_post_date,
        trim(CUSTNMBR) as customer_id,
        trim(CUSTNAME) as customer_name,
        nullif(trim(SLPRSNID), '') as salesperson_id,
        nullif(trim(SALSTERR), '') as territory_id,
        nullif(trim(CURNCYID), '') as currency_id,
        nullif(trim(PYMTRMID), '') as payment_terms_id,
        cast(SUBTOTAL as numeric(19, 2)) as subtotal_amount,
        cast(DOCAMNT as numeric(19, 2)) as total_doc_amount,
        cast(FRTAMNT as numeric(19, 2)) as freight_amount,
        cast(MISCAMNT as numeric(19, 2)) as misc_amount,
        cast(TAXAMNT as numeric(19, 2)) as tax_amount,
        cast(TRDISAMT as numeric(19, 2)) as trade_discount_amount,
        cast(DISCDLND as numeric(19, 2)) as discount_dollars_amount,
        cast(VOIDSTTS as integer) as is_voided
    from source
    where SOPNUMBE is not null and trim(SOPNUMBE) != ''
)

select * from renamed_and_cleaned
