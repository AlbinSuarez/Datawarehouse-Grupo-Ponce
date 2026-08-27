{{ config(materialized='table') }}

with sales_headers as (
    select * from {{ ref('stg_gp_sop30200_sales_headers') }}
    where is_voided = 0
      and sop_type in (3, 4) -- 3: Factura, 4: Devolución
),

sales_lines as (
    select * from {{ ref('stg_gp_sop30300_sales_lines') }}
    where sop_type in (3, 4)
),

items as (
    select * from {{ ref('stg_gp_iv00101_items') }}
),

joined as (
    select
        -- Llaves
        l.invoice_number,
        l.line_item_sequence,
        l.component_sequence,
        
        -- Fechas
        h.document_date,
        h.gl_post_date,
        cast(strftime(h.document_date, '%Y%m%d') as integer) as document_date_sk,
        cast(strftime(h.gl_post_date, '%Y%m%d') as integer) as gl_post_date_sk,

        -- Dimensiones Naturales
        h.customer_id,
        l.item_number,
        coalesce(h.salesperson_id, 'UNKNOWN_SP') as salesperson_id,
        coalesce(h.territory_id, 'UNKNOWN_TERR') as territory_id,
        h.currency_id,
        l.uofm,
        l.location_code,

        -- Atributos Documento
        h.sop_type,
        h.document_type_name,
        h.doc_id,

        -- Multiplicador por tipo de documento (Facturas +, Devoluciones -)
        case when h.sop_type = 4 then -1.0 else 1.0 end as direction_multiplier,

        -- Métricas normalizadas de línea
        (case when h.sop_type = 4 then -1.0 else 1.0 end) * l.quantity as net_quantity,
        l.unit_price,
        (case when h.sop_type = 4 then -1.0 else 1.0 end) * l.extended_price as gross_sales_amount,
        l.unit_cost,
        (case when h.sop_type = 4 then -1.0 else 1.0 end) * l.extended_cost as total_cost_amount,
        l.markdown_amount,

        -- Cálculo de Venta Neta y Margen Bruto
        ((case when h.sop_type = 4 then -1.0 else 1.0 end) * l.extended_price) - coalesce(l.markdown_amount, 0) as net_sales_amount,
        (((case when h.sop_type = 4 then -1.0 else 1.0 end) * l.extended_price) - coalesce(l.markdown_amount, 0)) - 
            ((case when h.sop_type = 4 then -1.0 else 1.0 end) * l.extended_cost) as gross_profit_amount,
        
        -- Margen Bruto %
        case 
            when (((case when h.sop_type = 4 then -1.0 else 1.0 end) * l.extended_price) - coalesce(l.markdown_amount, 0)) != 0
            then (
                (((case when h.sop_type = 4 then -1.0 else 1.0 end) * l.extended_price) - coalesce(l.markdown_amount, 0)) - 
                ((case when h.sop_type = 4 then -1.0 else 1.0 end) * l.extended_cost)
            ) * 100.0 / (((case when h.sop_type = 4 then -1.0 else 1.0 end) * l.extended_price) - coalesce(l.markdown_amount, 0))
            else 0.0
        end as gross_profit_margin_pct

    from sales_lines l
    inner join sales_headers h
        on l.invoice_number = h.invoice_number
       and l.sop_type = h.sop_type
    left join items i
        on l.item_number = i.item_number
)

select * from joined
