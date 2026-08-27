{{ config(materialized='table') }}

with staging_customers as (
    select * from {{ ref('stg_gp_rm00101_customers') }}
),

classes as (
    select * from {{ ref('stg_gp_rm00201_customer_classes') }}
),

final as (
    select
        -- Clave Subrogada Sintética
        md5(concat(c.customer_id, '_', coalesce(cast(c.modified_at as varchar), 'INITIAL'))) as customer_sk,
        c.customer_id,
        c.customer_name,
        coalesce(c.customer_class_id, 'UNKNOWN') as customer_class_id,
        coalesce(cl.customer_class_description, 'Sin Clasificación') as customer_class_desc,
        c.corporate_customer_id,
        c.primary_contact_person as primary_contact,
        c.address_line1,
        c.city,
        c.state,
        c.zip_code,
        c.country,
        c.phone_number_1 as phone_number,
        coalesce(c.salesperson_id, 'UNKNOWN_SP') as salesperson_id,
        coalesce(c.territory_id, 'UNKNOWN_TERR') as territory_id,
        c.payment_terms_id,
        coalesce(c.credit_limit_amount, 0.00) as credit_limit_amount,
        c.credit_limit_type,
        c.is_inactive as is_inactive_source,
        
        -- SCD2 Metadata Attributes
        coalesce(c.created_at, timestamp '2000-01-01 00:00:00') as valid_from,
        timestamp '9999-12-31 23:59:59' as valid_to,
        true as is_current,
        md5(concat_ws('|', c.customer_name, coalesce(c.customer_class_id, ''), coalesce(c.salesperson_id, ''), coalesce(c.territory_id, ''), cast(c.credit_limit_amount as varchar))) as row_hash

    from staging_customers c
    left join classes cl on c.customer_class_id = cl.customer_class_id
)

select * from final
