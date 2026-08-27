// Dashboard Web Dinámico - Grupo Ponce
// Control de Estado Global y Gráficos ApexCharts

let chartInstances = {};
let globalCustomers = [];
let globalInventoryItems = [];
let globalArCustomers = [];
let metaFilterData = {};

document.addEventListener("DOMContentLoaded", () => {
    initFilterOptions();
    refreshAllData();
});

// Navegación de Tabs
function switchTab(tabId) {
    document.querySelectorAll(".tab-content").forEach(el => el.classList.add("hidden"));
    document.querySelectorAll(".tab-btn").forEach(el => {
        el.classList.remove("bg-sky-600", "text-white");
        el.classList.add("text-slate-300");
    });

    const activeView = document.getElementById(`view-${tabId}`);
    const activeBtn = document.getElementById(`tab-${tabId}`);

    if (activeView && activeBtn) {
        activeView.classList.remove("hidden");
        activeBtn.classList.add("bg-sky-600", "text-white");
        activeBtn.classList.remove("text-slate-300");
    }

    // Control de visibilidad de filtros según el Tab activo
    const salesFilters = document.getElementById("salesFilterGroup");
    const invFilters = document.getElementById("invFilterGroup");

    if (tabId === 'inventory') {
        if (salesFilters) salesFilters.classList.add("hidden");
        if (invFilters) invFilters.classList.remove("hidden");
        fetchInventoryData();
    } else if (tabId === 'ar') {
        if (salesFilters) salesFilters.classList.remove("hidden");
        if (invFilters) invFilters.classList.add("hidden");
        fetchReceivablesData();
    } else {
        if (salesFilters) salesFilters.classList.remove("hidden");
        if (invFilters) invFilters.classList.add("hidden");
    }

    setTimeout(() => {
        window.dispatchEvent(new Event('resize'));
        if (window.lucide) lucide.createIcons();
    }, 100);
}

// Cargar opciones de filtros desde la API
async function initFilterOptions() {
    try {
        const res = await fetch("/api/meta/filters");
        const meta = await res.json();
        metaFilterData = meta;

        document.getElementById("lblServer").textContent = meta.database_target || "localhost";

        const selTerr = document.getElementById("filterTerritory");
        selTerr.innerHTML = '<option value="ALL">Todas las Zonas / Territorios</option>';
        meta.territories.forEach(t => {
            const opt = document.createElement("option");
            opt.value = t;
            opt.textContent = `Zona: ${t}`;
            selTerr.appendChild(opt);
        });

        const selClass = document.getElementById("filterClass");
        selClass.innerHTML = '<option value="ALL">Todas las Clases</option>';
        meta.customer_classes.forEach(c => {
            const opt = document.createElement("option");
            opt.value = c;
            opt.textContent = `Clase: ${c}`;
            selClass.appendChild(opt);
        });

        const selSp = document.getElementById("filterSalesperson");
        selSp.innerHTML = '<option value="ALL">Todos los Vendedores</option>';
        meta.salespeople.forEach(s => {
            const opt = document.createElement("option");
            opt.value = s;
            opt.textContent = `Vendedor: ${s}`;
            selSp.appendChild(opt);
        });

        if (meta.latest_rate) {
            const elRate = document.getElementById("lblRate");
            if (elRate) elRate.textContent = `${meta.latest_rate.toFixed(2)} Bs/USD`;
            const elRateDate = document.getElementById("lblRateDate");
            if (elRateDate && meta.latest_rate_date) {
                elRateDate.textContent = `(${meta.latest_rate_date} • ${meta.exchange_table || 'USD-VENTAS'})`;
            }
        }
    } catch (err) {
        console.error("Error al cargar metadatos de filtros:", err);
    }
}

// Filtrar Vendedores en Cascada según la Zona / Territorio seleccionada
function onTerritoryChange() {
    const selTerr = document.getElementById("filterTerritory").value;
    const selSp = document.getElementById("filterSalesperson");
    const currentSelectedSp = selSp.value;

    selSp.innerHTML = '<option value="ALL">Todos los Vendedores</option>';

    let availableSp = [];
    if (selTerr === "ALL") {
        availableSp = metaFilterData.salespeople || [];
    } else if (metaFilterData.salespeople_by_territory && metaFilterData.salespeople_by_territory[selTerr]) {
        availableSp = metaFilterData.salespeople_by_territory[selTerr];
    }

    availableSp.forEach(s => {
        const opt = document.createElement("option");
        opt.value = s;
        opt.textContent = `Vendedor: ${s}`;
        selSp.appendChild(opt);
    });

    if (availableSp.includes(currentSelectedSp)) {
        selSp.value = currentSelectedSp;
    } else {
        selSp.value = "ALL";
    }

    refreshAllData();
}

// Sincronización en Tiempo Real con SQL Server
async function triggerDatabaseReload() {
    const btn = document.getElementById("btnRefreshData");
    if (btn) {
        btn.innerHTML = `<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin"></i> Sincronizando BD...`;
        btn.disabled = true;
        if (window.lucide) lucide.createIcons();
    }

    try {
        const res = await fetch("/api/meta/reload", { method: "POST" });
        const info = await res.json();
        console.log("Base de datos sincronizada en tiempo real:", info);
        await initFilterOptions();
    } catch (err) {
        console.error("Error al sincronizar con la base de datos:", err);
    } finally {
        if (btn) {
            btn.innerHTML = `<i data-lucide="refresh-cw" class="w-3.5 h-3.5"></i> Sincronizar BD`;
            btn.disabled = false;
            if (window.lucide) lucide.createIcons();
        }
    }

    refreshAllData();
}

// Recargar datos al cambiar cualquier filtro
function refreshAllData() {
    const activeTab = document.querySelector(".tab-btn.bg-sky-600");
    const tabId = activeTab ? activeTab.id.replace("tab-", "") : "ventas";

    fetchVentasData();
    fetchChurnData();
    fetchLtvData();
    if (tabId === 'inventory') fetchInventoryData();
    if (tabId === 'ar') fetchReceivablesData();
}

function getFilterParams() {
    const territory = document.getElementById("filterTerritory").value;
    const customer_class = document.getElementById("filterClass").value;
    const salesperson = document.getElementById("filterSalesperson").value;

    const params = new URLSearchParams();
    if (territory !== "ALL") params.append("territory", territory);
    if (customer_class !== "ALL") params.append("customer_class", customer_class);
    if (salesperson !== "ALL") params.append("salesperson", salesperson);
    return params.toString();
}

// Renderizador Helper de ApexCharts
function renderChart(elementId, options) {
    if (chartInstances[elementId]) {
        chartInstances[elementId].destroy();
    }
    const el = document.getElementById(elementId);
    if (!el) return;
    el.innerHTML = "";
    const chart = new ApexCharts(el, options);
    chart.render();
    chartInstances[elementId] = chart;
}

// =========================================================================
// TAB 1: VENTAS & MARGEN
// =========================================================================
async function fetchVentasData() {
    const qs = getFilterParams();
    try {
        const [kpiRes, trendRes, terrRes, catRes] = await Promise.all([
            fetch(`/api/kpis/summary?${qs}`),
            fetch(`/api/sales/trends?${qs}`),
            fetch(`/api/sales/by-territory?${qs}`),
            fetch(`/api/sales/by-category?${qs}`)
        ]);

        const kpis = await kpiRes.json();
        const trends = await trendRes.json();
        const territories = await terrRes.json();
        const categories = await catRes.json();

        // Actualizar KPIs Scorecards
        document.getElementById("kpiNetSales").textContent = `$${kpis.net_sales.toLocaleString('es-DO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        document.getElementById("kpiGrossMargin").textContent = `${kpis.gross_margin_pct.toFixed(1)}%`;
        document.getElementById("kpiGrossProfitVal").textContent = `$${kpis.gross_profit.toLocaleString('es-DO', { minimumFractionDigits: 2 })} Utilidad Bruta`;
        document.getElementById("kpiChurnRate").textContent = `${kpis.churn_rate_pct.toFixed(1)}%`;
        document.getElementById("kpiChurnCount").textContent = `${kpis.churned_customers_count} Clientes Inactivos (90d)`;
        document.getElementById("kpiAvgLtv").textContent = `$${kpis.average_customer_ltv.toLocaleString('es-DO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        document.getElementById("kpiTotalCustScope").textContent = `${kpis.total_customers_in_scope} Clientes en Filtro`;

        // Chart 1: Tendencia Mensual Ventas & Margen
        const trendDates = trends.map(t => t.month);
        const trendSales = trends.map(t => t.sales);
        const trendGp = trends.map(t => t.gross_profit);

        const trendOptions = {
            series: [
                { name: "Ventas Netas ($ USD)", type: "column", data: trendSales },
                { name: "Utilidad Bruta ($ USD)", type: "line", data: trendGp }
            ],
            chart: { height: 300, type: "line", toolbar: { show: false }, background: "transparent" },
            stroke: { width: [0, 3], curve: "smooth" },
            plotOptions: { bar: { columnWidth: "50%", borderRadius: 4 } },
            colors: ["#0284c7", "#10b981"],
            theme: { mode: "dark" },
            xaxis: { categories: trendDates, labels: { style: { colors: "#94a3b8" } } },
            yaxis: [
                { labels: { style: { colors: "#94a3b8" }, formatter: val => `$${(val/1000).toFixed(0)}k` } },
                { opposite: true, labels: { style: { colors: "#94a3b8" }, formatter: val => `$${(val/1000).toFixed(0)}k` } }
            ],
            grid: { borderColor: "#334155", strokeDashArray: 4 },
            legend: { labels: { colors: "#cbd5e1" } },
            tooltip: { shared: true, intersect: false, y: { formatter: val => `$${Number(val).toLocaleString('es-DO', { minimumFractionDigits: 2 })} USD` } }
        };
        renderChart("chartSalesTrend", trendOptions);

        // Chart 2: Ventas por Territorio (Donut)
        const terrLabels = territories.map(t => t.territory_name || t.territory_id);
        const terrSales = territories.map(t => t.sales);
        const terrOptions = {
            series: terrSales,
            chart: { type: "donut", height: 300, background: "transparent" },
            labels: terrLabels,
            colors: ["#0ea5e9", "#6366f1", "#10b981", "#f59e0b", "#ec4899", "#8b5cf6", "#14b8a6", "#f43f5e"],
            theme: { mode: "dark" },
            legend: { position: "bottom", labels: { colors: "#cbd5e1" } },
            dataLabels: { enabled: true, formatter: val => `${val.toFixed(1)}%` },
            tooltip: { y: { formatter: val => `$${Number(val).toLocaleString('es-DO', { minimumFractionDigits: 2 })} USD` } }
        };
        renderChart("chartTerritorySales", terrOptions);

        // Chart 3: Ventas por Categoría (Barra Horizontal)
        const catLabels = categories.slice(0, 10).map(c => c.category_id);
        const catSales = categories.slice(0, 10).map(c => c.sales);
        const catOptions = {
            series: [{ name: "Ventas ($ USD)", data: catSales }],
            chart: { type: "bar", height: 280, toolbar: { show: false }, background: "transparent" },
            colors: ["#6366f1"],
            theme: { mode: "dark" },
            plotOptions: { bar: { horizontal: true, borderRadius: 6 } },
            xaxis: { categories: catLabels, labels: { style: { colors: "#94a3b8" }, formatter: val => `$${(val/1000).toFixed(0)}k` } },
            yaxis: { labels: { style: { colors: "#94a3b8" } } },
            grid: { borderColor: "#334155", strokeDashArray: 4 },
            tooltip: { y: { formatter: val => `$${Number(val).toLocaleString('es-DO', { minimumFractionDigits: 2 })} USD` } }
        };
        renderChart("chartCategorySales", catOptions);

    } catch (err) {
        console.error("Error cargando Ventas:", err);
    }
}

// =========================================================================
// TAB 2: CHURN & RETENCIÓN
// =========================================================================
async function fetchChurnData() {
    const qs = getFilterParams();
    try {
        const res = await fetch(`/api/churn/analysis?${qs}`);
        const data = await res.json();

        const periods = data.churn_history.map(c => c.period);
        const churnRates = data.churn_history.map(c => c.churn_rate_pct);
        const activeCusts = data.churn_history.map(c => c.active_customers);
        const churnedCusts = data.churn_history.map(c => c.churned_customers);

        // Chart 1: Evolución de Churn Rate (%)
        const churnOptions = {
            series: [{ name: "Tasa de Churn (%)", data: churnRates }],
            chart: { type: "area", height: 280, toolbar: { show: false }, background: "transparent" },
            stroke: { curve: "smooth", width: 3 },
            colors: ["#f43f5e"],
            theme: { mode: "dark" },
            fill: { type: "gradient", gradient: { shadeIntensity: 1, opacityFrom: 0.45, opacityTo: 0.05 } },
            xaxis: { categories: periods, labels: { style: { colors: "#94a3b8" } } },
            yaxis: { labels: { style: { colors: "#94a3b8" }, formatter: val => `${val.toFixed(1)}%` } },
            grid: { borderColor: "#334155", strokeDashArray: 4 }
        };
        renderChart("chartChurnRateTrend", churnOptions);

        // Chart 2: Activos vs Churned
        const barOptions = {
            series: [
                { name: "Clientes Activos", data: activeCusts },
                { name: "Clientes Churned (Inactivos)", data: churnedCusts }
            ],
            chart: { type: "bar", height: 280, stacked: true, toolbar: { show: false }, background: "transparent" },
            colors: ["#10b981", "#f43f5e"],
            theme: { mode: "dark" },
            plotOptions: { bar: { borderRadius: 4, columnWidth: "45%" } },
            xaxis: { categories: periods, labels: { style: { colors: "#94a3b8" } } },
            yaxis: { labels: { style: { colors: "#94a3b8" } } },
            legend: { labels: { colors: "#cbd5e1" } },
            grid: { borderColor: "#334155", strokeDashArray: 4 }
        };
        renderChart("chartActiveVsChurned", barOptions);

        // Render Tabla de Cohortes
        const tbody = document.getElementById("cohortTableBody");
        tbody.innerHTML = "";
        data.cohort_matrix.forEach(c => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td class="p-3 font-semibold text-sky-400">${c.cohort_month}</td>
                <td class="p-3 font-semibold text-slate-200">${c.new_customers}</td>
                <td class="p-3 text-center ${getCohortColor(c.m0)}">${c.m0}%</td>
                <td class="p-3 text-center ${getCohortColor(c.m1)}">${c.m1}%</td>
                <td class="p-3 text-center ${getCohortColor(c.m2)}">${c.m2}%</td>
                <td class="p-3 text-center ${getCohortColor(c.m3)}">${c.m3}%</td>
                <td class="p-3 text-center ${getCohortColor(c.m4)}">${c.m4}%</td>
                <td class="p-3 text-center ${getCohortColor(c.m5)}">${c.m5}%</td>
            `;
            tbody.appendChild(tr);
        });

    } catch (err) {
        console.error("Error cargando Churn:", err);
    }
}

function getCohortColor(val) {
    if (val >= 80) return "bg-emerald-500/20 text-emerald-300 font-bold";
    if (val >= 50) return "bg-sky-500/20 text-sky-300";
    if (val >= 25) return "bg-amber-500/20 text-amber-300";
    return "bg-rose-500/20 text-rose-300";
}

// =========================================================================
// TAB 3: LTV & SEGMENTACIÓN RFM
// =========================================================================
async function fetchLtvData() {
    const qs = getFilterParams();
    try {
        const res = await fetch(`/api/customers/rfm-ltv?${qs}`);
        const data = await res.json();

        globalCustomers = data.customers;

        // Chart 1: Donut RFM Segments
        const rfmLabels = data.rfm_summary.map(s => s.segment);
        const rfmCounts = data.rfm_summary.map(s => s.customer_count);
        const rfmColors = ["#10b981", "#0ea5e9", "#f59e0b", "#8b5cf6", "#f43f5e"];

        const rfmOptions = {
            series: rfmCounts,
            chart: { type: "donut", height: 280, background: "transparent" },
            labels: rfmLabels,
            colors: rfmColors,
            theme: { mode: "dark" },
            legend: { position: "bottom", labels: { colors: "#cbd5e1" } },
            dataLabels: { enabled: true, formatter: val => `${val.toFixed(1)}%` }
        };
        renderChart("chartRfmSegments", rfmOptions);

        // Chart 2: Top 10 Clientes por LTV
        const top10 = data.customers.slice(0, 10);
        const topLabels = top10.map(c => c.customer_name.length > 20 ? c.customer_name.substring(0, 20) + "..." : c.customer_name);
        const topLtvVals = top10.map(c => c.customer_ltv_gross_profit);

        const topOptions = {
            series: [{ name: "LTV Utilidad ($ USD)", data: topLtvVals }],
            chart: { type: "bar", height: 280, toolbar: { show: false }, background: "transparent" },
            colors: ["#f59e0b"],
            theme: { mode: "dark" },
            plotOptions: { bar: { horizontal: true, borderRadius: 6 } },
            xaxis: { categories: topLabels, labels: { style: { colors: "#94a3b8" }, formatter: val => `$${(val/1000).toFixed(0)}k` } },
            yaxis: { labels: { style: { colors: "#94a3b8" } } },
            grid: { borderColor: "#334155", strokeDashArray: 4 },
            tooltip: { y: { formatter: val => `$${Number(val).toLocaleString('es-DO', { minimumFractionDigits: 2 })} USD` } }
        };
        renderChart("chartTopLtv", topOptions);

        // Render Tabla RFM Rendimiento
        const rfmBody = document.getElementById("rfmTableBody");
        rfmBody.innerHTML = "";
        data.rfm_summary.forEach(s => {
            const tr = document.createElement("tr");
            let recAction = "Mantener fidelización";
            if (s.segment === "En Riesgo") recAction = "Campaña de reactivación / Visita comercial";
            if (s.segment === "Campeones / VIP") recAction = "Trato preferencial y acuerdos de volumen";
            if (s.segment === "Inactivos / Perdidos") recAction = "Ofertas especiales de reenganche";

            tr.innerHTML = `
                <td class="p-3 font-semibold text-white">${s.segment}</td>
                <td class="p-3 text-center text-sky-400 font-bold">${s.customer_count}</td>
                <td class="p-3 text-right font-mono">${s.avg_recency_days} días</td>
                <td class="p-3 text-right font-mono">$${s.total_sales.toLocaleString('es-DO', { minimumFractionDigits: 2 })}</td>
                <td class="p-3 text-right font-mono text-amber-400 font-bold">$${s.avg_ltv.toLocaleString('es-DO', { minimumFractionDigits: 2 })}</td>
                <td class="p-3 text-center"><span class="px-2 py-0.5 rounded-full text-[11px] bg-slate-800 text-slate-300 border border-slate-700">${recAction}</span></td>
            `;
            rfmBody.appendChild(tr);
        });

        // Render Tabla 360 Clientes
        renderCustomerTable(globalCustomers);

    } catch (err) {
        console.error("Error cargando LTV:", err);
    }
}

// =========================================================================
// TAB 4: FICHA 360° CLIENTES
// =========================================================================
function renderCustomerTable(customers) {
    const tbody = document.getElementById("customerTableBody");
    tbody.innerHTML = "";

    customers.forEach(c => {
        const tr = document.createElement("tr");
        tr.className = "hover:bg-slate-800/40 transition-colors";

        let segColor = "bg-slate-700 text-slate-300";
        if (c.rfm_segment === "Campeones / VIP") segColor = "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30";
        if (c.rfm_segment === "Leales Potenciales") segColor = "bg-sky-500/20 text-sky-400 border border-sky-500/30";
        if (c.rfm_segment === "En Riesgo") segColor = "bg-amber-500/20 text-amber-400 border border-amber-500/30";
        if (c.rfm_segment === "Inactivos / Perdidos") segColor = "bg-rose-500/20 text-rose-400 border border-rose-500/30";

        tr.innerHTML = `
            <td class="p-3 font-mono font-bold text-sky-400">${c.customer_id}</td>
            <td class="p-3 text-white font-medium">${c.customer_name}</td>
            <td class="p-3 text-slate-400">${c.customer_class_id}</td>
            <td class="p-3 text-slate-300">${c.territory_name}</td>
            <td class="p-3 text-center"><span class="px-2 py-0.5 rounded-full text-[10px] font-semibold ${segColor}">${c.rfm_segment}</span></td>
            <td class="p-3 text-right font-mono">${c.total_orders}</td>
            <td class="p-3 text-right font-mono text-slate-200">$${c.total_net_sales.toLocaleString('es-DO', { minimumFractionDigits: 2 })}</td>
            <td class="p-3 text-right font-mono font-bold text-amber-400">$${c.customer_ltv_gross_profit.toLocaleString('es-DO', { minimumFractionDigits: 2 })}</td>
            <td class="p-3 text-right font-mono text-slate-400">${c.recency_days}d</td>
            <td class="p-3 text-center">
                <button onclick="openModal360('${c.customer_id}')" class="px-2.5 py-1 bg-slate-800 hover:bg-sky-600 text-slate-200 hover:text-white rounded-lg text-xs font-semibold transition-colors flex items-center gap-1 mx-auto">
                    <i data-lucide="eye" class="w-3.5 h-3.5"></i> Ficha
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });

    if (window.lucide) lucide.createIcons();
}

function filterCustomerTable() {
    const q = document.getElementById("custSearchInput").value.toLowerCase();
    const filtered = globalCustomers.filter(c => 
        c.customer_id.toLowerCase().includes(q) ||
        c.customer_name.toLowerCase().includes(q) ||
        c.territory_name.toLowerCase().includes(q) ||
        c.customer_class_id.toLowerCase().includes(q)
    );
    renderCustomerTable(filtered);
}

function exportCustomersCSV() {
    let csv = "Codigo_Cliente,Nombre_Cliente,Clase,Zona,Segmento_RFM,Total_Pedidos,Ventas_USD,LTV_USD,Recencia_Dias\n";
    globalCustomers.forEach(c => {
        csv += `"${c.customer_id}","${c.customer_name}","${c.customer_class_id}","${c.territory_name}","${c.rfm_segment}",${c.total_orders},${c.total_net_sales},${c.customer_ltv_gross_profit},${c.recency_days}\n`;
    });

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `Clientes_Grupo_Ponce_${new Date().toISOString().slice(0,10)}.csv`;
    link.click();
}

// Modal Ficha 360°
async function openModal360(customerId) {
    try {
        const res = await fetch(`/api/customers/${customerId}/360`);
        const data = await res.json();

        document.getElementById("modalCustName").textContent = data.profile.customer_name;
        document.getElementById("modalCustId").textContent = `${data.profile.customer_id} • Clase: ${data.profile.customer_class_id} • Zona: ${data.profile.territory_name}`;
        document.getElementById("modalSales").textContent = `$${data.metrics.total_sales.toLocaleString('es-DO', { minimumFractionDigits: 2 })}`;
        document.getElementById("modalLTV").textContent = `$${data.metrics.total_gross_profit.toLocaleString('es-DO', { minimumFractionDigits: 2 })}`;
        document.getElementById("modalOrders").textContent = data.metrics.total_orders;
        document.getElementById("modalAOV").textContent = `$${data.metrics.average_order_value.toLocaleString('es-DO', { minimumFractionDigits: 2 })}`;

        const tbody = document.getElementById("modalTrxBody");
        tbody.innerHTML = "";
        data.recent_transactions.forEach(t => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td class="p-2 font-bold text-sky-400">${t.invoice_number}</td>
                <td class="p-2 text-slate-400">${t.document_date.slice(0,10)}</td>
                <td class="p-2"><span class="px-1.5 py-0.5 rounded text-[10px] ${t.document_type_id === 4 ? 'bg-rose-500/20 text-rose-300' : 'bg-emerald-500/20 text-emerald-300'}">${t.document_type_id === 4 ? 'Devolución' : 'Factura'}</span></td>
                <td class="p-2 text-slate-200">${t.item_description || t.item_id}</td>
                <td class="p-2 text-right">${t.quantity}</td>
                <td class="p-2 text-right text-slate-200">$${t.net_sales_amount.toFixed(2)}</td>
                <td class="p-2 text-right text-emerald-400 font-semibold">$${t.gross_profit_amount.toFixed(2)}</td>
            `;
            tbody.appendChild(tr);
        });

        document.getElementById("modal360").classList.remove("hidden");
        if (window.lucide) lucide.createIcons();
    } catch (e) {
        console.error("Error abriendo modal 360:", e);
    }
}

function closeModal360() {
    document.getElementById("modal360").classList.add("hidden");
}

// =========================================================================
// TAB 5: INVENTARIOS & STOCK
// =========================================================================
async function fetchInventoryData() {
    try {
        const skuType = document.getElementById("filterSkuType") ? document.getElementById("filterSkuType").value : "ALL";

        const [kpiRes, locRes, healthRes, catRes, itemsRes] = await Promise.all([
            fetch(`/api/inventory/kpis?sku_type=${skuType}`),
            fetch(`/api/inventory/by-location?sku_type=${skuType}`),
            fetch(`/api/inventory/health-summary?sku_type=${skuType}`),
            fetch(`/api/inventory/by-category?sku_type=${skuType}`),
            fetch(`/api/inventory/items?sku_type=${skuType}`)
        ]);

        const kpis = await kpiRes.json();
        const locations = await locRes.json();
        const health = await healthRes.json();
        const categories = await catRes.json();
        const items = await itemsRes.json();

        globalInventoryItems = items;

        // Render KPIs
        document.getElementById("kpiInvValuation").textContent = `$${kpis.total_valuation_usd.toLocaleString('es-DO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        document.getElementById("kpiInvUnits").textContent = `${kpis.total_units_on_hand.toLocaleString('es-DO', { maximumFractionDigits: 0 })} Unidades Físicas`;
        document.getElementById("kpiInvTurnover").textContent = `${kpis.inventory_turnover}x`;
        document.getElementById("kpiInvCogs").textContent = `$${kpis.annual_cogs_usd.toLocaleString('es-DO', { maximumFractionDigits: 0 })} Costo Ventas (COGS)`;
        document.getElementById("kpiInvDio").textContent = `${kpis.days_inventory_outstanding} días`;
        document.getElementById("kpiInvStockouts").textContent = kpis.stockout_items_count;
        document.getElementById("kpiInvAtRisk").textContent = `${kpis.at_risk_items_count} Artículos en Riesgo Crítico`;

        // Chart 1: Por Almacén
        const locLabels = locations.map(l => l.location_code);
        const locSeries = locations.map(l => l.total_valuation_usd);
        const locOptions = {
            series: locSeries,
            chart: { type: "donut", height: 280, background: "transparent" },
            labels: locLabels,
            colors: ["#0ea5e9", "#6366f1", "#10b981", "#f59e0b", "#ec4899", "#8b5cf6"],
            theme: { mode: "dark" },
            legend: { position: "bottom", labels: { colors: "#cbd5e1" } },
            dataLabels: { enabled: true, formatter: val => `${val.toFixed(1)}%` },
            tooltip: {
                y: { formatter: val => `$${Number(val).toLocaleString('es-DO', { minimumFractionDigits: 2 })} USD` }
            }
        };
        renderChart("chartInvLocation", locOptions);

        // Chart 2: Semáforo de Salud
        const healthLabels = health.map(h => h.health_status);
        const healthSeries = health.map(h => h.items_count);
        const healthColors = {
            "Nivel Óptimo": "#10b981",
            "Sobreinventario": "#38bdf8",
            "Riesgo Crítico": "#f59e0b",
            "Quiebre de Stock (Stockout)": "#f43f5e"
        };
        const chartColors = healthLabels.map(l => healthColors[l] || "#94a3b8");

        const healthOptions = {
            series: healthSeries,
            chart: { type: "pie", height: 280, background: "transparent" },
            labels: healthLabels,
            colors: chartColors,
            theme: { mode: "dark" },
            legend: { position: "bottom", labels: { colors: "#cbd5e1" } }
        };
        renderChart("chartInvHealth", healthOptions);

        // Chart 3: Por Categoría
        const catLabels = categories.slice(0, 8).map(c => c.category);
        const catValues = categories.slice(0, 8).map(c => c.total_valuation_usd);
        const catOptions = {
            series: [{ name: "Valoración ($ USD)", data: catValues }],
            chart: { type: "bar", height: 280, toolbar: { show: false }, background: "transparent" },
            colors: ["#10b981"],
            theme: { mode: "dark" },
            plotOptions: { bar: { horizontal: true, borderRadius: 6 } },
            xaxis: { categories: catLabels, labels: { style: { colors: "#94a3b8" }, formatter: val => `$${val.toLocaleString()}` } },
            yaxis: { labels: { style: { colors: "#94a3b8" } } },
            grid: { borderColor: "#334155", strokeDashArray: 4 },
            tooltip: { y: { formatter: val => `$${Number(val).toLocaleString('es-DO', { minimumFractionDigits: 2 })} USD` } }
        };
        renderChart("chartInvCategory", catOptions);

        // Render Tabla de Artículos
        renderInventoryTable(globalInventoryItems);

    } catch (e) {
        console.error("Error fetching inventory data:", e);
    }
}

function renderInventoryTable(items) {
    const tbody = document.getElementById("inventoryTableBody");
    tbody.innerHTML = "";

    items.forEach(i => {
        const tr = document.createElement("tr");
        tr.className = "hover:bg-slate-800/40 transition-colors";

        let badgeColor = "bg-slate-700 text-slate-300";
        if (i.health_status === "Nivel Óptimo") badgeColor = "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30";
        else if (i.health_status === "Sobreinventario") badgeColor = "bg-sky-500/20 text-sky-400 border border-sky-500/30";
        else if (i.health_status === "Riesgo Crítico") badgeColor = "bg-amber-500/20 text-amber-400 border border-amber-500/30";
        else if (i.health_status.includes("Quiebre")) badgeColor = "bg-rose-500/20 text-rose-400 border border-rose-500/30";

        let skuBadge = "bg-slate-700 text-slate-300";
        if (i.sku_type === "PT") skuBadge = "bg-sky-500/20 text-sky-300 border border-sky-500/30";
        else if (i.sku_type === "MP") skuBadge = "bg-purple-500/20 text-purple-300 border border-purple-500/30";
        else if (i.sku_type === "ME") skuBadge = "bg-amber-500/20 text-amber-300 border border-amber-500/30";

        const dioDisplay = i.dio >= 999 ? "∞ / Sin Venta" : `${i.dio}d`;

        tr.innerHTML = `
            <td class="p-3 font-bold text-sky-400">${i.item_number}</td>
            <td class="p-3 text-white font-medium">${i.item_description}</td>
            <td class="p-3 text-slate-400 font-sans flex items-center gap-1.5">
                <span class="px-1.5 py-0.5 rounded text-[10px] font-bold ${skuBadge}">${i.sku_type}</span>
                <span>${i.category}</span>
            </td>
            <td class="p-3 text-right">${i.qty_on_hand.toLocaleString()}</td>
            <td class="p-3 text-right text-slate-400">${i.qty_allocated.toLocaleString()}</td>
            <td class="p-3 text-right font-bold ${i.qty_available <= 0 ? 'text-rose-400' : 'text-emerald-400'}">${i.qty_available.toLocaleString()}</td>
            <td class="p-3 text-right text-indigo-400">${i.qty_on_order.toLocaleString()}</td>
            <td class="p-3 text-right text-slate-300">$${i.unit_cost_usd.toFixed(2)}</td>
            <td class="p-3 text-right text-amber-400 font-bold">$${i.total_valuation_usd.toLocaleString('es-DO', { minimumFractionDigits: 2 })}</td>
            <td class="p-3 text-right text-slate-300">${dioDisplay}</td>
            <td class="p-3 text-center"><span class="px-2 py-0.5 rounded-full text-[10px] font-semibold ${badgeColor}">${i.health_status}</span></td>
        `;
        tbody.appendChild(tr);
    });
}

function filterInventoryTable() {
    const q = document.getElementById("invSearchInput").value.toLowerCase();
    const health = document.getElementById("filterInvHealth").value;

    const filtered = globalInventoryItems.filter(i => {
        const matchesQuery = i.item_number.toLowerCase().includes(q) ||
                             i.item_description.toLowerCase().includes(q) ||
                             i.category.toLowerCase().includes(q) ||
                             (i.sku_type && i.sku_type.toLowerCase().includes(q));
        const matchesHealth = health === "ALL" || i.health_status === health;
        return matchesQuery && matchesHealth;
    });

    renderInventoryTable(filtered);
}

function exportInventoryCSV() {
    let csv = "Codigo_Articulo,Descripcion,Tipo_SKU,Categoria,Stock_Fisico,Comprometido,Disponible,En_Transito,Costo_Unitario_USD,Valoracion_USD,Rotacion_Turnover,DIO_Dias,Estado_Salud\n";
    globalInventoryItems.forEach(i => {
        csv += `"${i.item_number}","${i.item_description}","${i.sku_type}","${i.category}",${i.qty_on_hand},${i.qty_allocated},${i.qty_available},${i.qty_on_order},${i.unit_cost_usd},${i.total_valuation_usd},${i.inventory_turnover},${i.dio},"${i.health_status}"\n`;
    });

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `Inventario_Grupo_Ponce_${new Date().toISOString().slice(0,10)}.csv`;
    link.click();
}

// =========================================================================
// TAB 6: CUENTAS POR COBRAR (RECEIVABLES / AR)
// =========================================================================
async function fetchReceivablesData() {
    const qs = getFilterParams();
    try {
        const [kpiRes, agingRes, terrRes, spRes, custsRes] = await Promise.all([
            fetch(`/api/ar/kpis?${qs}`),
            fetch(`/api/ar/aging-summary?${qs}`),
            fetch(`/api/ar/by-territory?${qs}`),
            fetch(`/api/ar/by-salesperson?${qs}`),
            fetch(`/api/ar/customers?${qs}`)
        ]);

        const kpis = await kpiRes.json();
        const aging = await agingRes.json();
        const territories = await terrRes.json();
        const salespeople = await spRes.json();
        const customers = await custsRes.json();

        globalArCustomers = customers;

        // Render KPIs
        document.getElementById("kpiArTotal").textContent = `$${kpis.total_ar_balance_usd.toLocaleString('es-DO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        document.getElementById("kpiArDocsCount").textContent = `${kpis.open_documents_count} Documentos Abiertos`;
        document.getElementById("kpiArDso").textContent = `${kpis.dso_days} días`;
        document.getElementById("kpiArSales90d").textContent = `$${kpis.sales_90d_usd.toLocaleString('es-DO', { maximumFractionDigits: 0 })} Ventas 90d`;
        document.getElementById("kpiArOverdue").textContent = `$${kpis.total_overdue_usd.toLocaleString('es-DO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        document.getElementById("kpiArDelinquencyRate").textContent = `${kpis.delinquency_rate_pct.toFixed(1)}% Índice de Morosidad`;
        document.getElementById("kpiArCurrent").textContent = `$${kpis.total_current_usd.toLocaleString('es-DO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        document.getElementById("kpiArCustCount").textContent = `${kpis.customers_with_debt_count} Clientes con Deuda`;

        // Chart 1: Aging Report
        const agingLabels = aging.map(a => a.aging_bucket);
        const agingValues = aging.map(a => a.total_balance_usd);
        const agingColors = ["#10b981", "#f59e0b", "#f97316", "#ef4444", "#a855f7"];

        const agingOptions = {
            series: [{ name: "Saldo por Cobrar ($ USD)", data: agingValues }],
            chart: { type: "bar", height: 280, toolbar: { show: false }, background: "transparent" },
            colors: agingColors,
            theme: { mode: "dark" },
            plotOptions: { bar: { distributed: true, borderRadius: 6, columnWidth: "50%" } },
            xaxis: { categories: agingLabels, labels: { style: { colors: "#94a3b8", fontSize: "10px" } } },
            yaxis: { labels: { style: { colors: "#94a3b8" }, formatter: val => `$${(val/1000).toFixed(0)}k` } },
            grid: { borderColor: "#334155", strokeDashArray: 4 },
            legend: { show: false },
            tooltip: { y: { formatter: val => `$${Number(val).toLocaleString('es-DO', { minimumFractionDigits: 2 })} USD` } }
        };
        renderChart("chartArAging", agingOptions);

        // Chart 2: Cartera por Territorio (Donut)
        const terrLabels = territories.map(t => t.territory_name);
        const terrValues = territories.map(t => t.total_ar_usd);
        const terrOptions = {
            series: terrValues,
            chart: { type: "donut", height: 280, background: "transparent" },
            labels: terrLabels,
            colors: ["#0ea5e9", "#6366f1", "#10b981", "#f59e0b", "#ec4899", "#8b5cf6", "#14b8a6", "#f43f5e"],
            theme: { mode: "dark" },
            legend: { position: "bottom", labels: { colors: "#cbd5e1" } },
            dataLabels: { enabled: true, formatter: val => `${val.toFixed(1)}%` },
            tooltip: { y: { formatter: val => `$${Number(val).toLocaleString('es-DO', { minimumFractionDigits: 2 })} USD` } }
        };
        renderChart("chartArTerritory", terrOptions);

        // Chart 3: Cartera por Vendedor (Barra Horizontal)
        const spLabels = salespeople.slice(0, 8).map(s => s.salesperson_name);
        const spValues = salespeople.slice(0, 8).map(s => s.total_ar_usd);
        const spOptions = {
            series: [{ name: "Cartera Total ($ USD)", data: spValues }],
            chart: { type: "bar", height: 280, toolbar: { show: false }, background: "transparent" },
            colors: ["#10b981"],
            theme: { mode: "dark" },
            plotOptions: { bar: { horizontal: true, borderRadius: 6 } },
            xaxis: { categories: spLabels, labels: { style: { colors: "#94a3b8" }, formatter: val => `$${(val/1000).toFixed(0)}k` } },
            yaxis: { labels: { style: { colors: "#94a3b8" } } },
            grid: { borderColor: "#334155", strokeDashArray: 4 },
            tooltip: { y: { formatter: val => `$${Number(val).toLocaleString('es-DO', { minimumFractionDigits: 2 })} USD` } }
        };
        renderChart("chartArSalesperson", spOptions);

        // Render Tabla de Cartera por Cliente
        renderArTable(globalArCustomers);

    } catch (e) {
        console.error("Error fetching receivables data:", e);
    }
}

function renderArTable(customers) {
    const tbody = document.getElementById("arTableBody");
    tbody.innerHTML = "";

    customers.forEach(c => {
        const tr = document.createElement("tr");
        tr.className = "hover:bg-slate-800/40 transition-colors";

        let riskBadge = "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30";
        if (c.risk_status.includes("Alto")) riskBadge = "bg-rose-500/20 text-rose-400 border border-rose-500/30";
        else if (c.risk_status.includes("Moderado")) riskBadge = "bg-amber-500/20 text-amber-400 border border-amber-500/30";

        const limitDisplay = c.credit_limit_usd > 0 ? `$${c.credit_limit_usd.toLocaleString('es-DO', { maximumFractionDigits: 0 })}` : "Sin Límite";
        const utilDisplay = c.credit_limit_usd > 0 ? `${c.credit_utilization_pct}%` : "—";
        const overdueDisplay = c.max_overdue_days > 0 ? `${c.max_overdue_days}d` : "Al día";

        tr.innerHTML = `
            <td class="p-3 font-bold text-sky-400">${c.customer_id}</td>
            <td class="p-3 text-white font-medium font-sans">${c.customer_name}</td>
            <td class="p-3 text-slate-300 font-sans">${c.territory_name}</td>
            <td class="p-3 text-slate-400 font-sans">${c.salesperson_name}</td>
            <td class="p-3 text-right font-bold text-amber-400">$${c.total_debt_usd.toLocaleString('es-DO', { minimumFractionDigits: 2 })}</td>
            <td class="p-3 text-right text-emerald-400">$${c.current_debt_usd.toLocaleString('es-DO', { minimumFractionDigits: 2 })}</td>
            <td class="p-3 text-right font-bold ${c.overdue_debt_usd > 0 ? 'text-rose-400' : 'text-slate-400'}">$${c.overdue_debt_usd.toLocaleString('es-DO', { minimumFractionDigits: 2 })}</td>
            <td class="p-3 text-right text-slate-400">${limitDisplay}</td>
            <td class="p-3 text-right text-slate-300 font-semibold">${utilDisplay}</td>
            <td class="p-3 text-right ${c.max_overdue_days > 0 ? 'text-rose-400 font-bold' : 'text-emerald-400'}">${overdueDisplay}</td>
            <td class="p-3 text-center"><span class="px-2 py-0.5 rounded-full text-[10px] font-semibold ${riskBadge}">${c.risk_status}</span></td>
            <td class="p-3 text-center">
                <button onclick="openModalAr('${c.customer_id}', '${c.customer_name.replace(/'/g, "\\'")}')" class="px-2.5 py-1 bg-slate-800 hover:bg-sky-600 text-slate-200 hover:text-white rounded-lg text-xs font-semibold transition-colors flex items-center gap-1 mx-auto">
                    <i data-lucide="file-text" class="w-3.5 h-3.5"></i> Ver (${c.docs_count})
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });

    if (window.lucide) lucide.createIcons();
}

function filterArTable() {
    const q = document.getElementById("arSearchInput").value.toLowerCase();
    const agingFilter = document.getElementById("filterArAging").value;

    const filtered = globalArCustomers.filter(c => {
        const matchesQuery = c.customer_id.toLowerCase().includes(q) ||
                             c.customer_name.toLowerCase().includes(q) ||
                             c.territory_name.toLowerCase().includes(q) ||
                             c.salesperson_name.toLowerCase().includes(q);
        
        let matchesAging = true;
        if (agingFilter === "OVERDUE") matchesAging = c.overdue_debt_usd > 0;
        if (agingFilter === "CURRENT") matchesAging = c.overdue_debt_usd <= 0;

        return matchesQuery && matchesAging;
    });

    renderArTable(filtered);
}

function exportArCSV() {
    let csv = "Codigo_Cliente,Nombre_Cliente,Zona,Vendedor,Saldo_Total_USD,Saldo_Al_Dia_USD,Saldo_Vencido_USD,Limite_Credito_USD,Utilizacion_Pct,Max_Atraso_Dias,Estado_Riesgo,Total_Documentos\n";
    globalArCustomers.forEach(c => {
        csv += `"${c.customer_id}","${c.customer_name}","${c.territory_name}","${c.salesperson_name}",${c.total_debt_usd},${c.current_debt_usd},${c.overdue_debt_usd},${c.credit_limit_usd},${c.credit_utilization_pct},${c.max_overdue_days},"${c.risk_status}",${c.docs_count}\n`;
    });

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `Cartera_Cobranzas_Grupo_Ponce_${new Date().toISOString().slice(0,10)}.csv`;
    link.click();
}

// Modal Facturas por Cobrar (AR)
async function openModalAr(customerId, customerName) {
    try {
        const res = await fetch(`/api/ar/customer/${customerId}/invoices`);
        const invoices = await res.json();

        document.getElementById("modalArCustName").textContent = customerName;
        document.getElementById("modalArCustId").textContent = `Código: ${customerId} • ${invoices.length} Documentos Pendientes de Cobro`;

        const tbody = document.getElementById("modalArTrxBody");
        tbody.innerHTML = "";

        invoices.forEach(inv => {
            const tr = document.createElement("tr");

            let statusBadge = "bg-emerald-500/20 text-emerald-400";
            if (inv.overdue_days > 0) statusBadge = "bg-rose-500/20 text-rose-400";

            tr.innerHTML = `
                <td class="p-2.5 font-bold text-sky-400">${inv.doc_number}</td>
                <td class="p-2.5 text-slate-300">${inv.doc_type_desc}</td>
                <td class="p-2.5 text-slate-400">${inv.doc_date}</td>
                <td class="p-2.5 text-slate-400">${inv.due_date}</td>
                <td class="p-2.5 text-right text-slate-300">$${inv.orig_amount_usd.toLocaleString('es-DO', { minimumFractionDigits: 2 })}</td>
                <td class="p-2.5 text-right font-bold text-amber-400">$${inv.balance_usd.toLocaleString('es-DO', { minimumFractionDigits: 2 })}</td>
                <td class="p-2.5 text-center ${inv.overdue_days > 0 ? 'text-rose-400 font-bold' : 'text-emerald-400'}">${inv.overdue_days > 0 ? `${inv.overdue_days}d` : 'Al día'}</td>
                <td class="p-2.5 text-center"><span class="px-2 py-0.5 rounded-full text-[10px] font-semibold ${statusBadge}">${inv.aging_bucket}</span></td>
            `;
            tbody.appendChild(tr);
        });

        document.getElementById("modalArInvoices").classList.remove("hidden");
        if (window.lucide) lucide.createIcons();
    } catch (e) {
        console.error("Error abriendo facturas de AR:", e);
    }
}

function closeModalAr() {
    document.getElementById("modalArInvoices").classList.add("hidden");
}
