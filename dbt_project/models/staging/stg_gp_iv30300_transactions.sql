{{ config(materialized='view') }}

with source as (
    select * from {{ source('dynamics_gp', 'IV30300') }}
),

renamed as (
    select
        cast(DOCTYPE as integer) as doc_type,
        case cast(DOCTYPE as integer)
            when 1 then 'Ajuste Entrada (+)'
            when 2 then 'Ajuste Salida (-)'
            when 3 then 'Transferencia'
            when 4 then 'Venta'
            when 5 then 'Recepción Compra'
            when 6 then 'Devolución'
            else 'Otro'
        end as doc_type_desc,
        trim(DOCNUMBR) as doc_number,
        cast(DOCDATE as date) as doc_date,
        trim(ITEMNMBR) as item_number,
        coalesce(nullif(trim(TRXLOCTN), ''), 'DEFAULT_LOC') as from_location_code,
        nullif(trim(TRNSTLOC), '') as to_location_code,
        cast(TRXQTY as numeric(19, 4)) as trx_qty,
        cast(UNITCOST as numeric(19, 4)) as unit_cost_vef,
        cast(EXTDCOST as numeric(19, 2)) as extended_cost_vef
    from source
    where ITEMNMBR is not null and trim(ITEMNMBR) != ''
)

select * from renamed
