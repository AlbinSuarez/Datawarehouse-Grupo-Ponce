{{ config(materialized='table') }}

with date_spine as (
    -- Genera calendario desde 2015 hasta 2035
    select 
        dateadd('day', i, date '2015-01-01') as full_date
    from range(0, 7670) as t(i)
),

final as (
    select
        cast(strftime(full_date, '%Y%m%d') as integer) as date_sk,
        full_date,
        day(full_date) as day_of_month,
        month(full_date) as month_number,
        strftime(full_date, '%B') as month_name,
        quarter(full_date) as quarter_number,
        year(full_date) as year_number,
        dayofweek(full_date) as day_of_week,
        strftime(full_date, '%A') as day_name,
        case when dayofweek(full_date) in (1, 7) then true else false end as is_weekend,
        false as is_holiday
    from date_spine
)

select * from final
