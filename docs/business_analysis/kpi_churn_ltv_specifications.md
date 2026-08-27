# Especificación de KPIs: Churn & LTV (Customer Lifetime Value)
**Rol**: Senior Data Warehouse Business Analyst & Requirements Engineer  
**Proyecto**: Data Mart de Clientes y Ventas - Grupo Ponce  
**Fuente Origen**: Microsoft Dynamics GP (`RM00101`, `RM00201`, `SOP30200`, `SOP30300`, `RM20101`)

---

## 1. Enterprise Bus Matrix de Kimball

Mapeo de los procesos de negocio con las dimensiones conformadas de la organización:

| Proceso de Negocio / Mart | `dim_customer` (SCD2) | `dim_product` | `dim_salesperson` | `dim_territory` | `dim_date` | `dim_document_type` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Ventas Transaccionales (`fact_sales`)** | **X** | **X** | **X** | **X** | **X** | **X** |
| **Snapshot Mensual Cliente (`fact_customer_monthly_snapshot`)** | **X** | | **X** | **X** | **X** | |
| **Cuentas por Cobrar (`fact_receivables_aging`)** | **X** | | **X** | **X** | **X** | **X** |
| **Movimientos de Inventario (`fact_inventory`)** | | **X** | | | **X** | **X** |

---

## 2. Definición y Fórmulas de KPIs

### 2.1. Customer Churn Rate (Tasa de Cancelación / Deserción de Clientes)

#### Definición de Negocio
Porcentaje de clientes activos al inicio de un periodo temporal (mes/trimestre) que cesan su actividad comercial (no registran compras válidas dentro de una ventana de inactividad definida) durante el periodo evaluado.

#### Reglas de Negocio Específicas
1. **Definición de Cliente Activo**: Un cliente se considera *Activo* en el mes $M$ si ha realizado al menos una transacción de compra válida (`SOPTYPE = 3`, `VOIDSTTS = 0`) en los últimos $N$ días (umbral estándar: **90 días**, equivalente a 1 trimestre).
2. **Definición de Cliente en Churn**: Un cliente que estaba activo en el periodo $M-1$ pero cuya última transacción superó el umbral de inactividad ($> 90$ días) sin realizar ninguna compra en el mes $M$.
3. **Exclusiones**:
   - Clientes marcados administrativamente como `INACTIVE = 1` en `RM00101` dentro de los primeros 15 días posteriores al alta sin haber comprado (cuentas de prueba o errores de digitación).
   - Documentos anulados (`VOIDSTTS = 1`) o tipos de documentos cotización/pedido no convertidos (`SOPTYPE IN (1, 2, 5)`).

#### Fórmula Matemática
$$\text{Monthly Churn Rate}_M = \left( \frac{\text{Clientes Churned en Mes } M}{\text{Clientes Activos al Inicio del Mes } M} \right) \times 100$$

#### Pseudo-SQL (Lógica Analítica)
```sql
WITH customer_monthly_activity AS (
    SELECT 
        customer_id,
        period_month,
        total_invoices_month,
        net_sales_amount_month,
        MAX(invoice_date) OVER (
            PARTITION BY customer_id 
            ORDER BY period_month 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS last_purchase_date_to_date
    FROM int_customer_churn_ltv_monthly
),
churn_classification AS (
    SELECT 
        customer_id,
        period_month,
        CASE 
            WHEN DATEDIFF('day', last_purchase_date_to_date, period_month) <= 90 THEN 1 
            ELSE 0 
        END AS is_active,
        LAG(CASE WHEN DATEDIFF('day', last_purchase_date_to_date, period_month) <= 90 THEN 1 ELSE 0 END) 
            OVER (PARTITION BY customer_id ORDER BY period_month) AS was_active_prev_month
    FROM customer_monthly_activity
)
SELECT 
    period_month,
    COUNT(DISTINCT CASE WHEN was_active_prev_month = 1 THEN customer_id END) AS active_start_month,
    COUNT(DISTINCT CASE WHEN was_active_prev_month = 1 AND is_active = 0 THEN customer_id END) AS churned_customers,
    ROUND(
        COUNT(DISTINCT CASE WHEN was_active_prev_month = 1 AND is_active = 0 THEN customer_id END) * 100.0 / 
        NULLIF(COUNT(DISTINCT CASE WHEN was_active_prev_month = 1 THEN customer_id END), 0), 
        2
    ) AS churn_rate_pct
FROM churn_classification
GROUP BY period_month
ORDER BY period_month;
```

---

### 2.2. Customer Lifetime Value (LTV / CLV)

#### Definición de Negocio
Valor económico total proyectado o histórico acumulado que un cliente genera a lo largo de toda su relación comercial con Grupo Ponce, restando devoluciones y bonificaciones.

#### Modelos de LTV
El Data Mart provee dos perspectivas:
1. **LTV Histórico (Realizado)**: Suma acumulada de margen bruto (o ingresos netos) generados por el cliente desde su primera orden de compra hasta la fecha actual.
2. **LTV Predictivo / Cohortes (Tradicional)**: Estimación del valor futuro por cohorte basada en el Ingreso Promedio por Cliente (ARPU) y la tasa de Churn.

#### Fórmulas Matemáticas

##### A. LTV Histórico por Cliente $i$ en el Momento $T$:
$$\text{Historical LTV}_i = \sum_{t=1}^{T} (\text{Ventas Netas}_{i,t} - \text{Costo Total de Ventas}_{i,t})$$

Donde:
- $\text{Ventas Netas}_{i,t} = \text{XTNDPRCE (Facturas)} - \text{XTNDPRCE (Devoluciones)} - \text{Descuentos Aplicados}$
- $\text{Costo Total}_{i,t} = \text{EXTDCOST (Facturas)} - \text{EXTDCOST (Devoluciones)}$

##### B. LTV Predictivo por Cohorte / Segmento:
$$\text{Predictive LTV} = \frac{\text{Average Revenue Per Account (ARPU)} \times \text{Gross Margin \%}}{\text{Customer Churn Rate}}$$

O mediante la frecuencia de compra y ticket promedio:
$$\text{LTV} = \text{Average Order Value (AOV)} \times \text{Purchase Frequency (PF)} \times \text{Customer Lifespan (ALS)}$$

Donde:
- $\text{AOV} = \frac{\text{Ingresos Netos Totales}}{\text{Número Total de Pedidos/Facturas}}$
- $\text{PF} = \frac{\text{Número Total de Pedidos}}{\text{Clientes Únicos}}$
- $\text{ALS (Años/Meses)} = \frac{1}{\text{Churn Rate}}$

#### Pseudo-SQL (Lógica Analítica)
```sql
SELECT 
    customer_id,
    customer_name,
    customer_class_id,
    first_purchase_date,
    last_purchase_date,
    DATEDIFF('day', first_purchase_date, last_purchase_date) AS customer_tenure_days,
    total_orders_count,
    total_gross_revenue,
    total_returns_amount,
    total_net_revenue,
    total_cogs,
    (total_net_revenue - total_cogs) AS historical_ltv_gross_profit,
    ROUND(total_net_revenue / NULLIF(total_orders_count, 0), 2) AS average_order_value,
    ROUND((total_net_revenue - total_cogs) * 100.0 / NULLIF(total_net_revenue, 0), 2) AS gross_margin_pct
FROM int_customer_orders_summary;
```

---

## 3. Dimensiones de Análisis y Cortes de Visualización (Slice & Dice)

Todos los KPIs deben ser consumibles y segmentables por:
1. **Dimensión Tiempo**: Año, Trimestre, Mes, Semana, Día (Fecha de Factura `DOCDATE` y Fecha Contable `GLPOSTDT`).
2. **Dimensión Cliente**: Clase de Cliente (`CUSTCLAS`), Territorio (`SALSTERR`), Límite de Crédito (`CRLMTAMT`), Antigüedad de Cohorte.
3. **Dimensión Vendedor**: Ejecutivo Asignado (`SLPRSNID`), Supervisor / Región.
4. **Dimensión Producto**: Clase de Artículo (`ITMCLSCD`), Línea de Producto, Categoría.
