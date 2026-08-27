# Arquitectura Dimensional: Data Mart de Inventarios
**Rol**: Enterprise Data Warehouse Architect  
**Proyecto**: Data Mart de Inventarios - Grupo Ponce  

---

## Diagrama Entidad-Relación (ERD) en Estrella

```mermaid
erDiagram
    dim_product ||--o{ fact_inventory_balance : "product_sk"
    dim_location ||--o{ fact_inventory_balance : "location_sk"
    dim_date ||--o{ fact_inventory_balance : "date_sk"

    dim_product ||--o{ fact_inventory_transactions : "product_sk"
    dim_location ||--o{ fact_inventory_transactions : "from_location_sk"
    dim_date ||--o{ fact_inventory_transactions : "trx_date_sk"

    dim_product {
        bigint product_sk PK
        varchar item_number "ITEMNMBR"
        varchar item_description "ITEMDESC"
        varchar category "ITMCLSCD"
        numeric standard_cost_usd
        numeric current_cost_usd
        tinyint is_active
    }

    dim_location {
        bigint location_sk PK
        varchar location_code "LOCNCODE"
        varchar location_name
        varchar location_type
        tinyint is_active
    }

    fact_inventory_balance {
        bigint balance_sk PK
        int date_sk FK
        bigint product_sk FK
        bigint location_sk FK
        numeric qty_on_hand "Stock Físico"
        numeric qty_allocated "Stock Comprometido"
        numeric qty_available "Stock Disponible (OnHand - Allocated)"
        numeric qty_on_order "Stock en Tránsito/Compras"
        numeric safety_stock_qty "Stock de Seguridad"
        numeric unit_cost_usd "Costo Unitario USD"
        numeric total_valuation_usd "Valoración en USD"
        numeric annualized_cogs_usd "Costo de Ventas Anualizado"
        numeric inventory_turnover "Ratio de Rotación"
        numeric days_inventory_outstanding "Días de Cobertura (DIO)"
        varchar stock_health_status "Óptimo / Riesgo / Quiebre / Exceso"
    }

    fact_inventory_transactions {
        bigint transaction_sk PK
        int trx_date_sk FK
        bigint product_sk FK
        bigint from_location_sk FK
        bigint to_location_sk FK
        smallint doc_type "1=Ajuste +, 2=Ajuste -, 3=Transf, 4=Venta, 5=Compra"
        varchar doc_number "DOCNUMBR"
        numeric trx_qty "Cantidad"
        numeric unit_cost_usd "Costo Unitario USD"
        numeric extended_cost_usd "Costo Total USD"
    }
```
