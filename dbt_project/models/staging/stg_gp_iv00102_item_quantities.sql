{{ config(materialized='view') }}

with source as (
    select * from {{ source('dynamics_gp', 'IV00102') }}
),

renamed as (
    select
        trim(ITEMNMBR) as item_number,
        coalesce(nullif(trim(LOCNCODE), ''), 'TOTAL_GENERAL') as location_code,
        cast(RCRDTYPE as integer) as record_type, -- 1: Total general, 2: Por almacén
        cast(QTYONHND as numeric(19, 4)) as qty_on_hand,
        cast(ATYALLOC as numeric(19, 4)) as qty_allocated,
        cast(QTYONHND - ATYALLOC as numeric(19, 4)) as qty_available,
        cast(QTYONORD as numeric(19, 4)) as qty_on_order,
        cast(QTYBKORD as numeric(19, 4)) as qty_backorder,
        cast(SFTYSTCKQTY as numeric(19, 4)) as safety_stock_qty,
        cast(ORDRPNTQTY as numeric(19, 4)) as reorder_point_qty,
        cast(MNMMORDRQTY as numeric(19, 4)) as min_order_qty,
        cast(MXMMORDRQTY as numeric(19, 4)) as max_order_qty
    from source
    where ITEMNMBR is not null and trim(ITEMNMBR) != ''
)

select * from renamed
