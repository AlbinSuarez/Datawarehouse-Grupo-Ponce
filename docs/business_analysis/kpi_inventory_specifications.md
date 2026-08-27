# Especificación de KPIs de Inventario y Abastecimiento
**Rol**: Senior Data Warehouse Business Analyst & Requirements Engineer  
**Proyecto**: Data Mart de Inventarios - Grupo Ponce  
**Fuente Origen**: Microsoft Dynamics GP (`IV00101`, `IV00102`, `IV10200`, `IV30300`, `DYNAMICS.dbo.MC00100`)

---

## 1. Definición y Fórmulas de KPIs de Inventario

### 1.1. Valoración de Inventario en USD (Inventory Valuation)
- **Definición**: Valor monetario total del stock físico remanente en almacén valorizado según sus capas de recepción a costo de compra real o costo de reposición convertido a USD con la tasa cambiaria `USD-VENTAS`.
- **Fórmula**:
  $$\text{Valoración Total USD} = \sum_{i} \left( \frac{\text{Cantidad en Mano}_i \times \text{Costo Unitario VEF}_i}{\text{Tasa Cambiaria USD-VENTAS}} \right)$$

### 1.2. Rotación de Inventario (Inventory Turnover Ratio)
- **Definición**: Cantidad de ciclos en los que el inventario promedio es vendido y reabastecido durante un periodo anualizado.
- **Fórmula**:
  $$\text{Inventory Turnover} = \frac{\text{Costo Anualizado de Ventas (COGS USD)}}{\text{Valor Promedio del Inventario (USD)}}$$
- **Interpretación**:
  - $> 6.0$: Alta rotación (flujo rápido de mercancía).
  - $2.0 - 6.0$: Rotación estándar para productos farmacéuticos y de consumo masivo.
  - $< 2.0$: Baja rotación (riesgo de obsolescencia o capital inmovilizado).

### 1.3. Días de Inventario Disponible (DIO / DSI - Days Inventory Outstanding)
- **Definición**: Estimación del número de días que el inventario actual puede satisfacer la demanda comercial promedio sin reabastecimiento.
- **Fórmula**:
  $$\text{DIO} = \frac{\text{Valor de Inventario Actual USD}}{\text{COGS Diario USD}} = \frac{\text{Valor de Inventario Actual USD}}{\text{COGS Anual USD} / 365} = \frac{365}{\text{Inventory Turnover}}$$

### 1.4. Semáforo de Salud de Inventario y Quiebres (Stockouts)
- **Matriz de Clasificación**:
  1. 🔴 **Quiebre de Stock (Stockout)**: $\text{Stock Disponible} \le 0$ con demanda histórica activa en los últimos 90 días.
  2. 🟡 **Riesgo Crítico de Quiebre**: $\text{Stock Disponible} < \text{Stock de Seguridad (SFTYSTCKQTY)}$ o $\text{DIO} < 15\text{ días}$.
  3. 🟢 **Nivel Óptimo**: $15\text{ días} \le \text{DIO} \le 90\text{ días}$.
  4. 🔵 **Sobreinventario**: $\text{DIO} > 180\text{ días}$ (exceso de stock frente al ritmo de venta).
