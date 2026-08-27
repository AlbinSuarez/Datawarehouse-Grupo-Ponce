{{ config(materialized='view') }}

with source as (
    select * from {{ source('dynamics_gp', 'SOP30300') }}
),

renamed_and_cleaned as (
    select
        cast(SOPTYPE as integer) as sop_type,
        trim(SOPNUMBE) as invoice_number,
        cast(LNITMSEQ as integer) as line_item_sequence,
        cast(CMPNTSEQ as integer) as component_sequence,
        trim(ITEMNMBR) as item_number,
        trim(ITEMDESC) as item_description,
        nullif(trim(UOFM), '') as uofm,
        nullif(trim(LOCNCODE), '') as location_code,
        cast(DOCDATE as date) as document_date,
        trim(CUSTNMBR) as customer_id,
        cast(QUANTITY as numeric(19, 4)) as quantity,
        cast(UNITPRCE as numeric(19, 4)) as unit_price,
        cast(XTNDPRCE as numeric(19, 2)) as extended_price,
        cast(UNITCOST as numeric(19, 4)) as unit_cost,
        cast(EXTDCOST as numeric(19, 2)) as extended_cost,
        cast(MRKDNAMT as numeric(19, 2)) as markdown_amount
    from source
    where SOPNUMBE is not null and trim(SOPNUMBE) != ''
)

select * from renamed_and_cleaned
