{{ config(materialized='view') }}

with source as (
    select * from {{ source('dynamics_gp', 'IV10200') }}
),

renamed as (
    select
        trim(ITEMNMBR) as item_number,
        coalesce(nullif(trim(TRXLOCTN), ''), 'DEFAULT_LOC') as location_code,
        cast(DATERECD as date) as date_received,
        cast(RCTSEQNM as integer) as receipt_sequence_num,
        cast(QTYRECVD as numeric(19, 4)) as qty_received,
        cast(QTYSOLD as numeric(19, 4)) as qty_sold,
        cast(QTYRECVD - QTYSOLD as numeric(19, 4)) as qty_on_hand_layer,
        cast(UNITCOST as numeric(19, 4)) as unit_cost_vef,
        trim(RCPTNMBR) as receipt_number,
        nullif(trim(VENDORID), '') as vendor_id
    from source
    where (QTYRECVD - QTYSOLD) > 0
)

select * from renamed
