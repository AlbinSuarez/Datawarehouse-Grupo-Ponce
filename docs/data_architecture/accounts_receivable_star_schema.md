# Arquitectura Dimensional: Data Mart de Cuentas por Cobrar
**Rol**: Enterprise Data Warehouse Architect  
**Proyecto**: Data Mart de Cuentas por Cobrar - Grupo Ponce  

---

## Diagrama Entidad-Relación (ERD)

```mermaid
erDiagram
    dim_customer ||--o{ fact_receivables_open : "customer_sk"
    dim_salesperson ||--o{ fact_receivables_open : "salesperson_sk"
    dim_territory ||--o{ fact_receivables_open : "territory_sk"
    dim_date ||--o{ fact_receivables_open : "doc_date_sk"
    dim_date ||--o{ fact_receivables_open : "due_date_sk"

    fact_receivables_open {
        bigint ar_document_sk PK
        int doc_date_sk FK
        int due_date_sk FK
        bigint customer_sk FK
        bigint salesperson_sk FK
        bigint territory_sk FK
        varchar doc_number "DOCNUMBR"
        int doc_type "1=Factura, 3=ND, 7=NC, 8=Pago, 9=Dev"
        numeric orig_amount_usd
        numeric current_balance_usd
        int overdue_days "Días de Atraso"
        varchar aging_bucket "Corriente / 1-30 / 31-60 / 61-90 / >90"
        tinyint is_overdue "1=Vencido, 0=Al día"
    }

    dim_customer {
        bigint customer_sk PK
        varchar customer_id
        varchar customer_name
        varchar customer_class_id
        numeric credit_limit_usd
    }

    dim_salesperson {
        bigint salesperson_sk PK
        varchar salesperson_id
        varchar salesperson_name
    }

    dim_territory {
        bigint territory_sk PK
        varchar territory_id
        varchar territory_name
    }
```
