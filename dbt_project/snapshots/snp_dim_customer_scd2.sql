{% snapshot snp_dim_customer_scd2 %}

{{
    config(
      target_schema='snapshots',
      unique_key='customer_id',
      strategy='check',
      check_cols=[
          'customer_name',
          'customer_class_id',
          'corporate_customer_id',
          'salesperson_id',
          'territory_id',
          'payment_terms_id',
          'credit_limit_amount',
          'is_inactive'
      ]
    )
}}

select
    customer_id,
    customer_name,
    customer_class_id,
    corporate_customer_id,
    primary_contact_person,
    address_line1,
    city,
    state,
    zip_code,
    country,
    phone_number_1,
    salesperson_id,
    territory_id,
    payment_terms_id,
    credit_limit_amount,
    credit_limit_type,
    is_inactive,
    created_at,
    modified_at
from {{ ref('stg_gp_rm00101_customers') }}

{% endsnapshot %}
