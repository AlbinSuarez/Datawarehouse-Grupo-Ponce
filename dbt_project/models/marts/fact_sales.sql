{{ config(materialized='table') }}

with int_sales as (
    select * from {{ ref('int_sales_lines_enriched') }}
),

customers as (
    select * from {{ ref('dim_customer') }}
    where is_current = true
),

products as (
    select * from {{ ref('dim_product') }}
),

salespeople as (
    select * from {{ ref('dim_salesperson') }}
),

territories as (
    select * from {{ ref('dim_territory') }}
),

final as (
    select
        -- Surrogate Key del Hecho
        md5(concat(s.invoice_number, '_', cast(s.line_item_sequence as varchar), '_', cast(s.component_sequence as varchar))) as sales_fact_sk,
        
        -- Degenerate Dimensions (Identificadores)
        s.invoice_number,
        s.line_item_sequence,
        s.component_sequence,
        s.sop_type,
        s.document_type_name as doc_type_desc,
        s.doc_id,
        s.currency_id,
        s.uofm,
        s.location_code,

        -- Foreign Keys a Dimensiones
        s.document_date_sk,
        s.gl_post_date_sk,
        coalesce(c.customer_sk, md5('UNKNOWN_CUSTOMER')) as customer_sk,
        coalesce(p.product_sk, md5('UNKNOWN_PRODUCT')) as product_sk,
        coalesce(sp.salesperson_sk, md5('UNKNOWN_SP')) as salesperson_sk,
        coalesce(t.territory_sk, md5('UNKNOWN_TERR')) as territory_sk,

        -- Métricas Cuantitativas
        s.net_quantity as quantity,
        s.unit_price,
        s.gross_sales_amount as extended_price,
        s.unit_cost,
        s.total_cost_amount as extended_cost,
        coalesce(s.markdown_amount, 0.00) as markdown_amount,
        s.net_sales_amount,
        s.gross_profit_amount,
        s.gross_profit_margin_pct,
        0 as is_voided

    from int_sales s
    left join customers c on s.customer_id = c.customer_id
    left join products p on s.item_number = p.item_number
    left join salespeople sp on s.salesperson_id = sp.salesperson_id
    left join territories t on s.territory_id = t.territory_id
)

select * from final
