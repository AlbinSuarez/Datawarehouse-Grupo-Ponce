# Arquitectura del Data Mart: Esquema en Estrella con SCD Tipo 2
**Rol**: Enterprise Data Warehouse Architect  
**Proyecto**: Data Mart de Clientes y Ventas - Grupo Ponce  
**Fuente Origen**: Microsoft Dynamics GP (`RM00101`, `RM00201`, `RM00301`, `RM00303`, `SOP30200`, `SOP30300`, `IV00101`)

---

## 1. Diagrama Entidad-Relación (ERD) en Estrella

```mermaid
erDiagram
    dim_date ||--o{ fact_sales : "fecha_documento_sk / fecha_contable_sk"
    dim_customer_scd2 ||--o{ fact_sales : "customer_sk"
    dim_product ||--o{ fact_sales : "product_sk"
    dim_salesperson ||--o{ fact_sales : "salesperson_sk"
    dim_territory ||--o{ fact_sales : "territory_sk"
    
    dim_customer_scd2 ||--o{ fact_customer_monthly_snapshot : "customer_sk"
    dim_date ||--o{ fact_customer_monthly_snapshot : "year_month_sk"
    dim_territory ||--o{ fact_customer_monthly_snapshot : "territory_sk"
    dim_salesperson ||--o{ fact_customer_monthly_snapshot : "salesperson_sk"

    dim_customer_scd2 {
        bigint customer_sk PK "Surrogate Key (Hash/Sequence)"
        varchar customer_id "Natural Key (CUSTNMBR)"
        varchar customer_name "CUSTNAME"
        varchar customer_class_id "CUSTCLAS"
        varchar customer_class_desc "CLASDSCR"
        varchar corporate_customer_id "CPRCSTNM"
        varchar primary_contact "CNTCPRSN"
        varchar address_line1 "ADDRESS1"
        varchar city "CITY"
        varchar state "STATE"
        varchar zip_code "ZIP"
        varchar country "COUNTRY"
        varchar phone_number "PHONE1"
        varchar salesperson_id "SLPRSNID"
        varchar territory_id "SALSTERR"
        varchar payment_terms_id "PYMTRMID"
        numeric credit_limit_amount "CRLMTAMT"
        smallint credit_limit_type "CRLMTTYP"
        tinyint is_inactive_source "INACTIVE"
        timestamp valid_from "Effective Start Timestamp"
        timestamp valid_to "Effective End Timestamp (9999-12-31)"
        boolean is_current "Flag Registro Vigente"
        varchar row_hash "Hash Diff para detección de cambios"
    }

    dim_product {
        bigint product_sk PK "Surrogate Key"
        varchar item_number "Natural Key (ITEMNMBR)"
        varchar item_description "ITEMDESC"
        varchar item_class_code "ITMCLSCD"
        varchar item_generic_desc "ITMGEDSC"
        numeric standard_cost "STNDCOST"
        numeric current_cost "CURRCOST"
        varchar uom_schedule "UOMSCHDL"
        smallint decimal_places_qty "DECPLQTY"
        smallint decimal_places_curr "DECPLCUR"
        tinyint is_active "1=Activo, 0=Inactivo"
    }

    dim_salesperson {
        bigint salesperson_sk PK "Surrogate Key"
        varchar salesperson_id "Natural Key (SLPRSNID)"
        varchar employee_id "EMPLOYID"
        varchar full_name "Nombre Completo"
        varchar job_title "SPRNSTTL"
        varchar territory_id "SALSTERR"
        smallint commission_percent "COMPRCNT"
        tinyint is_inactive "INACTIVE"
    }

    dim_territory {
        bigint territory_sk PK "Surrogate Key"
        varchar territory_id "Natural Key (SALSTERR)"
        varchar territory_description "SLTERDSC"
        varchar manager_full_name "STMGRFNM + STMGRLNM"
        varchar country "COUNTRY"
        tinyint is_inactive "INACTIVE"
    }

    dim_date {
        int date_sk PK "YYYYMMDD"
        date full_date "Fecha Completa"
        int day_of_month "1-31"
        int month_number "1-12"
        varchar month_name "Enero, Febrero..."
        int quarter_number "1-4"
        int year_number "2024, 2025, 2026..."
        int day_of_week "1-7"
        varchar day_name "Lunes, Martes..."
        boolean is_weekend "True / False"
        boolean is_holiday "True / False"
    }

    fact_sales {
        bigint sales_fact_sk PK
        varchar invoice_number "SOPNUMBE"
        int line_item_sequence "LNITMSEQ"
        int component_sequence "CMPNTSEQ"
        int document_date_sk FK "dim_date"
        int gl_post_date_sk FK "dim_date"
        bigint customer_sk FK "dim_customer_scd2"
        bigint product_sk FK "dim_product"
        bigint salesperson_sk FK "dim_salesperson"
        bigint territory_sk FK "dim_territory"
        smallint sop_type "3=Factura, 4=Devolución"
        varchar doc_type_desc "Factura / Devolución"
        varchar doc_id "DOCID"
        varchar currency_id "CURNCYID"
        varchar uofm "UOFM"
        varchar location_code "LOCNCODE"
        numeric quantity "Cantidad Positiva / Negativa"
        numeric unit_price "UNITPRCE"
        numeric extended_price "XTNDPRCE (Venta Bruta)"
        numeric unit_cost "UNITCOST"
        numeric extended_cost "EXTDCOST (Costo Venta)"
        numeric markdown_amount "MRKDNAMT (Descuento)"
        numeric net_sales_amount "Venta Neta (Precio - Descuentos)"
        numeric gross_profit_amount "Margen Bruto (Venta Neta - Costo)"
        numeric gross_profit_margin_pct "Margen Bruto %"
        tinyint is_voided "0=Válida, 1=Anulada"
    }

    fact_customer_monthly_snapshot {
        bigint snapshot_sk PK
        int year_month_sk FK "YYYYMM01 en dim_date"
        bigint customer_sk FK "dim_customer_scd2"
        bigint salesperson_sk FK "dim_salesperson"
        bigint territory_sk FK "dim_territory"
        varchar customer_id "Natural Key"
        int active_month_flag "1 si compró en el mes, 0 si no"
        int is_churned_flag "1 si Churn (>90 días sin compra), 0 si no"
        int is_new_customer_flag "1 si su primera compra fue en este mes"
        int is_reactivated_flag "1 si reactivó compra tras haber estado en Churn"
        int total_invoices_month "Cantidad de facturas emitidas en el mes"
        int total_returns_month "Cantidad de notas de crédito/devolución"
        numeric gross_sales_month "Venta bruta en el mes"
        numeric returns_amount_month "Monto devuelto en el mes"
        numeric net_sales_month "Venta neta mensual"
        numeric total_cogs_month "Costo de mercancía vendida mensual"
        numeric gross_profit_month "Utilidad bruta mensual"
        numeric cumulative_net_sales_ltv "LTV Acumulado Histórico en Ventas"
        numeric cumulative_gross_profit_ltv "LTV Acumulado Histórico en Margen"
        int days_since_last_purchase "Días transcurridos desde última compra"
        date last_purchase_date "Fecha de la última compra registrada"
    }
```

---

## 2. Estrategia de SCD Tipo 2 para `dim_customer`

Para preservar el historial de los cambios organizacionales y comerciales del cliente (por ejemplo, cambios de Vendedor Asignado, Territorio, Clase de Cliente o Límite de Crédito), la tabla `dim_customer` implementa **Slowly Changing Dimensions Tipo 2**:

1. **Clave Subrogada (`customer_sk`)**: Hash MD5/SHA256 o autoincremental combinando `CUSTNMBR + valid_from`.
2. **Columnas de Control Temporal**:
   - `valid_from`: Timestamp exacto de inicio de vigencia de la versión.
   - `valid_to`: Timestamp de fin de vigencia (por defecto `9999-12-31 23:59:59` para la versión activa).
   - `is_current`: Booleano `TRUE` para el registro vigente, `FALSE` para versiones históricas.
   - `row_hash`: Hash MD5 de los atributos rastreados para detectar mutaciones en el proceso de ingesta.
3. **Mapeo de Nulos / Registros Especiales**:
   - `customer_sk = -1`: `Cliente Desconocido / No Asignado`.
   - `customer_sk = -2`: `No Aplica`.

---

## 3. Especificación de Tablas de Hechos (Fact Tables)

### A. `fact_sales` (Granularidad: 1 fila por línea de documento de venta)
- **Granularidad de Negocio**: Una línea de artículo vendida o devuelta en una factura/nota de crédito (`SOP30200` + `SOP30300`).
- **Manejo de Devoluciones (`SOPTYPE = 4`)**: Cantidad (`QUANTITY`), Monto Extendido (`XTNDPRCE`) y Costo Extendido (`EXTDCOST`) se almacenan con signo aritmético negativo o normalizado para agregación directa $\sum$.

### B. `fact_customer_monthly_snapshot` (Granularidad: 1 fila por cliente y mes calendario)
- **Granularidad de Negocio**: Estado mensual acumulado de cada cliente para análisis de retención, Churn, frecuencia de compra y LTV histórico.
- **Particionamiento**: Particionado por `year_month_sk` (por ejemplo, `20260101`, `20260201`).
