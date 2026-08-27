# Catálogo de Gobernanza, PII y Diccionario de Datos
**Rol**: Data Governance, Quality & Compliance Specialist  
**Proyecto**: Data Mart de Clientes y Ventas - Grupo Ponce  
**Estándar de Cumplimiento**: GDPR / Regulaciones Locales de Protección de Datos

---

## 1. Inventario y Clasificación de Datos Sensibles (PII)

Clasificación de atributos del maestro de clientes (`RM00101`) según nivel de sensibilidad:

| Campo Origen (GP) | Campo Dimensional | Categoría PII | Nivel de Sensibilidad | Política de Enmascaramiento / Seguridad |
| :--- | :--- | :--- | :--- | :--- |
| `CUSTNAME` | `customer_name` | Direct PII | **Confidencial** | Visible solo para analistas comerciales; enmascaramiento parcial en entornos QA (`Juan P***`). |
| `CNTCPRSN` | `primary_contact` | Direct PII | **Confidencial** | Hash SHA256 o anonimización para analítica abierta. |
| `PHONE1` / `PHONE2` | `phone_number` | Direct PII | **Restringido** | Enmascaramiento completo en reportes generales (`+1-***-***-1234`). |
| `FAX` | `fax_number` | Direct PII | **Restringido** | Enmascaramiento. |
| `ADDRESS1` / `2` | `address_line1` | Indirect PII | **Interno** | Uso restringido a logística y distribución. |
| `CITY` / `STATE` | `city` / `state` | Geográfico | **Público Interno** | Sin enmascaramiento (agregaciones regionales). |
| `CRLMTAMT` | `credit_limit_amount` | Financiero | **Restringido** | Control RBAC (Role-Based Access Control) solo para Finanzas / Crédito. |
| `CHEKBKID` | `checkbook_id` | Financiero | **Altamente Restringido** | Excluido de vistas de consumo general. |

---

## 2. Contrato de Datos (Data Contract) para Clientes & Ventas

```yaml
data_contract:
  dataset_name: "mart_sales.fact_sales"
  owner: "Data Engineering & Sales BI Team"
  sla:
    freshness: "Diario antes de las 06:00 AM UTC"
    availability: "99.9%"
  schema_contract:
    primary_keys: ["sales_fact_sk"]
    composite_uniqueness: ["invoice_number", "line_item_sequence", "component_sequence"]
    non_nullable_fields:
      - invoice_number
      - customer_sk
      - product_sk
      - document_date_sk
      - net_sales_amount
  quarantine_policy:
    enabled: true
    error_table: "mart_sales._quarantined_sales_records"
    action: "Desviar registros con clientes inexistentes o montos nulos a tabla de cuarentena sin interrumpir pipeline."
```

---

## 3. Matriz de Roles y Accesos (RBAC)

| Rol de Usuario | `dim_customer` (Atributos PII) | `fact_sales` (Métricas Financieras) | `fact_customer_monthly_snapshot` (KPIs Churn/LTV) |
| :--- | :---: | :---: | :---: |
| **Ejecutivo Comercial / Ventas** | Lectura Completa (su territorio) | Lectura Completa (su territorio) | Lectura Completa |
| **Analista BI / Marketing** | Enmascarado (PII anonimizada) | Lectura Completa | Lectura Completa |
| **Auditor Financiero** | Lectura Completa | Lectura Completa + Conciliación GP | Lectura Completa |
| **Data Scientist / ML Ops** | Tokenizado / Hashed | Lectura Completa Agregada | Lectura Completa |
