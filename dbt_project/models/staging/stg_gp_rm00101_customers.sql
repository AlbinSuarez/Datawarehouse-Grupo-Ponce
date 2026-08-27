{{ config(materialized='view') }}

with source as (
    select * from {{ source('dynamics_gp', 'RM00101') }}
),

renamed_and_cleaned as (
    select
        trim(CUSTNMBR) as customer_id,
        trim(CUSTNAME) as customer_name,
        nullif(trim(CUSTCLAS), '') as customer_class_id,
        nullif(trim(CPRCSTNM), '') as corporate_customer_id,
        nullif(trim(CNTCPRSN), '') as primary_contact_person,
        nullif(trim(STMTNAME), '') as statement_name,
        nullif(trim(SHRTNAME), '') as short_name,
        nullif(trim(ADDRESS1), '') as address_line1,
        nullif(trim(ADDRESS2), '') as address_line2,
        nullif(trim(CITY), '') as city,
        nullif(trim(STATE), '') as state,
        nullif(trim(ZIP), '') as zip_code,
        nullif(trim(COUNTRY), '') as country,
        nullif(trim(PHONE1), '') as phone_number_1,
        nullif(trim(PHONE2), '') as phone_number_2,
        nullif(trim(FAX), '') as fax_number,
        nullif(trim(SLPRSNID), '') as salesperson_id,
        nullif(trim(SALSTERR), '') as territory_id,
        nullif(trim(PYMTRMID), '') as payment_terms_id,
        nullif(trim(CHEKBKID), '') as checkbook_id,
        cast(CRLMTTYP as integer) as credit_limit_type,
        cast(CRLMTAMT as numeric(19, 2)) as credit_limit_amount,
        cast(CUSTDISC as numeric(8, 4)) / 100.0 as customer_discount_pct,
        cast(INACTIVE as integer) as is_inactive,
        cast(CREATDDT as timestamp) as created_at,
        cast(MODIFDT as timestamp) as modified_at
    from source
    where CUSTNMBR is not null and trim(CUSTNMBR) != ''
)

select * from renamed_and_cleaned
