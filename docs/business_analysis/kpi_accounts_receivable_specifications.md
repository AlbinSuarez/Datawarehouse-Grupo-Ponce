# Especificación de KPIs: Data Mart de Cuentas por Cobrar y Cobranzas
**Rol**: Senior Data Warehouse Business Analyst & Requirements Engineer  
**Proyecto**: Data Mart de Cuentas por Cobrar (Receivables Management) - Grupo Ponce  
**Fuente Origen**: Microsoft Dynamics GP (`RM20101`, `RM30101`, `RM20201`, `RM00103`, `DYNAMICS.dbo.MC00100`)

---

## 1. Definición y Fórmulas de KPIs de Cuentas por Cobrar

### 1.1. Días de Venta Pendientes de Cobro (DSO - Days Sales Outstanding)
- **Definición**: Número promedio de días que tarda la empresa en convertir sus ventas a crédito en efectivo líquido.
- **Fórmula**:
  $$\text{DSO} = \left( \frac{\text{Saldo Total de Cuentas por Cobrar (USD)}}{\text{Ventas Netas Totales (Últimos 90 Días USD)}} \right) \times 90$$
- **Benchmark Comercial**:
  - $< 45\text{ días}$: Nivel Excelente (Alta liquidez y cobranza eficiente).
  - $45 - 60\text{ días}$: Nivel Normal / Aceptable para canales de distribución farmacéutica.
  - $> 60\text{ días}$: Alerta de Iliquidez / Retención excesiva de capital de trabajo.

### 1.2. Antigüedad de la Cartera (Aging Buckets)
- **Definición**: Clasificación de la deuda según los días transcurridos respecto a la fecha de vencimiento acordada (`DUEDATE`).
  $$\text{Días de Vencimiento} = \text{Fecha Actual} - \text{Fecha de Vencimiento}$$
- **Rangos de Clasificación**:
  1. 🟢 **Corriente / No Vencido**: $\text{Días} \le 0$.
  2. 🟡 **Vencido 1 a 30 Días**: $1 \le \text{Días} \le 30$.
  3. 🟠 **Vencido 31 a 60 Días**: $31 \le \text{Días} \le 60$.
  4. 🔴 **Vencido 61 a 90 Días**: $61 \le \text{Días} \le 90$.
  5. 🟣 **Vencido > 90 Días (Moroso / Incobrable)**: $\text{Días} > 90$.

### 1.3. Índice de Morosidad (%)
- **Fórmula**:
  $$\text{Índice de Morosidad} = \left( \frac{\text{Saldo Vencido Total (> 0 Días USD)}}{\text{Saldo Total de la Cartera (USD)}} \right) \times 100$$

### 1.4. Utilización del Límite de Crédito
- **Fórmula**:
  $$\%\text{ Utilización de Crédito} = \left( \frac{\text{Saldo Pendiente Actual USD}}{\text{Límite de Crédito Aprobado (RM00101.CRLMTAMT USD)}} \right) \times 100$$
