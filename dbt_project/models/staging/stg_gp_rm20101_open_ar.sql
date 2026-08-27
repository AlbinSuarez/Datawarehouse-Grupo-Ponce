{{ config(materialized='view') }}

with source as (
    select * from {{ source('dynamics_gp', 'RM20101') }}
),

renamed as (
    select
        trim(CUSTNMBR) as customer_id,
        trim(DOCNUMBR) as doc_number,
        cast(RMDTYPAL as integer) as doc_type,
        case cast(RMDTYPAL as integer)
            when 1 then 'Factura'
            when 3 then 'Nota de Débito'
            when 7 then 'Nota de Crédito'
            when 8 then 'Pago / Cobro no Aplicado'
            when 9 then 'Devolución'
            else 'Otro'
        end as doc_type_desc,
        cast(DOCDATE as date) as doc_date,
        cast(DUEDATE as date) as due_date,
        cast(ORTRXAMT as numeric(19, 4)) as orig_amount_vef,
        cast(CURTRXAM as numeric(19, 4)) as current_balance_vef,
        trim(CURNCYID) as currency_id,
        nullif(trim(SLPRSNID), '') as salesperson_id,
        nullif(trim(SLSTERCD), '') as territory_id,
        trim(PYMTRMID) as payment_terms_id,
        cast(AGNGBUKT as integer) as gp_aging_bucket,
        cast(VOIDSTTS as integer) as void_status
    from source
    where CURTRXAM > 0 and VOIDSTTS = 0
)

select * from renamed
