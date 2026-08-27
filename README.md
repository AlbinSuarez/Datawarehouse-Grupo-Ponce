# Data Warehouse Empresarial Grupo Ponce (DW_PB)

Sistema integral de Data Warehouse y Business Intelligence para Grupo Ponce, integrando Microsoft Dynamics GP con modelos analíticos multidimensionales, Data Marts de Ventas, Clientes, Inventarios y Cuentas por Cobrar (AR), y Dashboard Web Interactivo.

## Arquitectura

- **Capa Transaccional:** Microsoft Dynamics GP (PB + DYNAMICS en SQL Server)
- **Capa Data Warehouse:** DW_PB (Esquema Estrella con SCD Tipo 1/2 y auditoría)
- **ETL Diario:** Procedimiento maestro \dbo.sp_ETL_Ejecutar_Carga_Diaria\ automatizado con SQL Server Agent cada 4 horas (desde las 06:00 AM)
- **Capa Analítica & KPIs:** FastAPI + Pandas + Uvicorn
- **Dashboard Web:** HTML5, Tailwind CSS, Lucide Icons, ApexCharts
- **Modelado dbt:** Staging, Intermediate y Marts dimensionales

## Módulos del Dashboard

1. **Ventas & Margen:** Ventas netas multimoneda (USD/VEF), margen bruto, tendencias mensuales y distribución por zona.
2. **Churn & Retención:** Tasa de deserción a 90 días, evolución mensual y matriz de cohortes M+0 a M+5.
3. **LTV & RFM:** Segmentación de clientes (*Campeones / VIP, Leales, En Riesgo, Inactivos*) y valor de vida de clientes.
4. **Ficha 360° de Clientes:** Perfil integral con historial de transacciones, pedidos y AOV.
5. **Inventarios & Stock:** Valoración USD, rotación (Turnover), DIO (días en inventario) y semáforo de salud de stock.
6. **Cuentas por Cobrar (AR):** Reporte de antigüedad de deuda (Aging), DSO, cartera por zona y vendedor.

## Ejecución Local

\\ash
# Instalar dependencias
pip install -r dashboard_app/requirements.txt

# Iniciar servidor analítico
python dashboard_app/run_dashboard.py
\
Acceso: \http://localhost:8000