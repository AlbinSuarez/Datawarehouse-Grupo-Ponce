{{ config(materialized='view') }}

with source as (
    select * from {{ source('dynamics_gp', 'IV00101') }}
),

renamed_and_cleaned as (
    select
        trim(ITEMNMBR) as item_number,
        trim(ITEMDESC) as item_description,
        nullif(trim(ITMCLSCD), '') as item_class_code,
        nullif(trim(ITMGEDSC), '') as item_generic_description,
        cast(STNDCOST as numeric(19, 4)) as standard_cost,
        cast(CURRCOST as numeric(19, 4)) as current_cost,
        nullif(trim(UOMSCHDL), '') as uom_schedule,
        cast(DECPLQTY as integer) as decimal_places_qty,
        cast(DECPLCUR as integer) as decimal_places_curr,
        cast(ITEMTRKOP as integer) as tracking_option,
        cast(INACTIVE as integer) as is_inactive
    from source
    where ITEMNMBR is not null and trim(ITEMNMBR) != ''
)

select * from renamed_and_cleaned
