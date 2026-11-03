/**
 * Aplicación cliente de visualización y exploración de datos INE Bolivia.
 * 100% Client-side: Tabulator + Chart.js + SheetJS.
 */

let manifest = null;
let activeIndicatorId = null;
let currentData = [];
let tableInstance = null;
let chartInstance = null;
let chartRangeFilter = "all";

// Inicialización de la aplicación
document.addEventListener("DOMContentLoaded", async () => {
  await loadManifest();
  setupEventListeners();
});

// Cargar catálogo de indicadores pre-compilado
async function loadManifest() {
  try {
    const res = await fetch("data/manifest.json");
    if (!res.ok) throw new Error("No se pudo cargar el catálogo manifest.json");
    manifest = await res.json();

    // Seleccionar primer indicador disponible por defecto
    const firstInd = Object.keys(manifest.indicators)[0];
    switchIndicator(firstInd);
  } catch (err) {
    console.error("Error al inicializar la aplicación:", err);
    document.getElementById("ind-title").innerText = "Error cargando datos";
    document.getElementById("ind-description").innerText = err.message;
  }
}

// Configurar escuchadores de eventos del DOM
function setupEventListeners() {
  // Navegación lateral de indicadores
  document.querySelectorAll(".nav-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const indId = btn.getAttribute("data-indicator-id");
      if (indId && indId !== activeIndicatorId) {
        switchIndicator(indId);
      }
    });
  });

  // Filtro de búsqueda general
  const searchInput = document.getElementById("table-search");
  searchInput.addEventListener("input", (e) => {
    const query = e.target.value.toLowerCase().trim();
    if (!tableInstance) return;

    if (!query) {
      applyFilters();
    } else {
      tableInstance.setFilter((data) => {
        return Object.values(data).some(val => 
          val !== null && val !== undefined && String(val).toLowerCase().includes(query)
        );
      });
      updateRowCount();
    }
  });

  // Filtro de año
  const yearSelect = document.getElementById("filter-year");
  yearSelect.addEventListener("change", applyFilters);

  // Filtro de variable secundaria
  const varSelect = document.getElementById("filter-variable");
  varSelect.addEventListener("change", applyFilters);

  // Botón Exportar CSV
  document.getElementById("btn-export-csv").addEventListener("click", () => {
    if (!tableInstance) return;
    tableInstance.download("csv", `${activeIndicatorId}_ine_bolivia.csv`);
  });

  // Botón Exportar Excel
  document.getElementById("btn-export-xlsx").addEventListener("click", () => {
    if (!tableInstance) return;
    tableInstance.download("xlsx", `${activeIndicatorId}_ine_bolivia.xlsx`, {
      sheetName: "Datos INE Bolivia"
    });
  });

  // Filtros de rango del gráfico
  document.querySelectorAll(".chart-controls .pill-btn").forEach(pill => {
    pill.addEventListener("click", () => {
      document.querySelectorAll(".chart-controls .pill-btn").forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      chartRangeFilter = pill.getAttribute("data-range");
      renderChart();
    });
  });
}

// Cambiar de indicador activo
async function switchIndicator(indId) {
  activeIndicatorId = indId;
  const meta = manifest.indicators[indId];
  if (!meta) return;

  // Actualizar clases activas en sidebar
  document.querySelectorAll(".nav-btn").forEach(btn => {
    btn.classList.toggle("active", btn.getAttribute("data-indicator-id") === indId);
  });

  // Actualizar títulos y descripciones
  document.getElementById("ind-category").innerText = meta.category;
  document.getElementById("ind-title").innerText = meta.title;
  document.getElementById("ind-description").innerText = meta.description;

  // Actualizar Tarjetas KPI
  document.getElementById("kpi-latest-val").innerText = meta.kpis.latest_val_formatted || "--";
  document.getElementById("kpi-latest-unit").innerText = meta.unit || "";
  document.getElementById("kpi-latest-date").innerText = `Período: ${meta.kpis.latest_date || "--"}`;

  document.getElementById("kpi-max-val").innerText = meta.kpis.max_val_formatted || "--";
  document.getElementById("kpi-max-unit").innerText = meta.unit || "";
  document.getElementById("kpi-max-date").innerText = `Período: ${meta.kpis.max_date || "--"}`;

  document.getElementById("kpi-min-val").innerText = meta.kpis.min_val_formatted || "--";
  document.getElementById("kpi-min-unit").innerText = meta.unit || "";
  document.getElementById("kpi-min-date").innerText = `Período: ${meta.kpis.min_date || "--"}`;

  document.getElementById("kpi-total-rows").innerText = meta.kpis.total_records.toLocaleString();
  document.getElementById("kpi-range-years").innerText = `Rango: ${meta.min_year} - ${meta.max_year}`;

  // Cargar el JSON estático pre-compilado
  try {
    const res = await fetch(`data/${indId}.json`);
    if (!res.ok) throw new Error(`No se pudo cargar el archivo data/${indId}.json`);
    currentData = await res.json();

    populateFilterDropdowns(meta);
    renderTable(meta);
    renderChart();
  } catch (err) {
    console.error("Error al cargar datos del indicador:", err);
  }
}

// Llenar listas desplegables de filtros
function populateFilterDropdowns(meta) {
  const yearSelect = document.getElementById("filter-year");
  yearSelect.innerHTML = '<option value="">Todos los años</option>';
  const years = [...new Set(currentData.map(d => d.anio))].sort((a, b) => b - a);
  years.forEach(y => {
    const opt = document.createElement("option");
    opt.value = y;
    opt.textContent = y;
    yearSelect.appendChild(opt);
  });

  // Filtro de variable secundaria (ej. departamento o actividad)
  const varContainer = document.getElementById("variable-filter-container");
  const varSelect = document.getElementById("filter-variable");
  const varKey = meta.category_column;

  if (varKey && currentData.length > 0 && currentData[0][varKey] !== undefined) {
    varContainer.style.display = "flex";
    varSelect.innerHTML = '<option value="">Todas las variables</option>';
    const distinctVars = [...new Set(currentData.map(d => d[varKey]))].sort();
    distinctVars.forEach(v => {
      const opt = document.createElement("option");
      opt.value = v;
      opt.textContent = v;
      varSelect.appendChild(opt);
    });
  } else {
    varContainer.style.display = "none";
  }

  document.getElementById("table-search").value = "";
}

// Aplicar filtros combinados
function applyFilters() {
  if (!tableInstance) return;

  const yearVal = document.getElementById("filter-year").value;
  const varVal = document.getElementById("filter-variable").value;
  const meta = manifest.indicators[activeIndicatorId];
  const varKey = meta?.category_column;

  const filters = [];
  if (yearVal) {
    filters.push({ field: "anio", type: "=", value: Number(yearVal) });
  }
  if (varVal && varKey) {
    filters.push({ field: varKey, type: "=", value: varVal });
  }

  tableInstance.setFilter(filters);
  updateRowCount();
}

// Actualizar contador de filas filtradas
function updateRowCount() {
  setTimeout(() => {
    if (tableInstance) {
      const count = tableInstance.getDataCount("active");
      document.getElementById("table-row-count").innerText = `${count.toLocaleString()} registros encontrados`;
    }
  }, 100);
}

// Construir e instanciar la tabla con Tabulator
function renderTable(meta) {
  const columns = meta.columns.map(col => {
    const isNum = col.type === "number" || col.type === "float" || col.type === "int";
    return {
      title: col.label,
      field: col.field,
      sorter: isNum ? "number" : "string",
      hozAlign: isNum ? "right" : "left",
      formatter: isNum ? (cell) => {
        const val = cell.getValue();
        if (val === null || val === undefined) return "-";
        return Number(val).toLocaleString("es-BO", { maximumFractionDigits: 2 });
      } : undefined
    };
  });

  tableInstance = new Tabulator("#data-table", {
    data: currentData,
    columns: columns,
    layout: "fitColumns",
    responsiveLayout: "collapse",
    pagination: "local",
    paginationSize: 20,
    paginationSizeSelector: [15, 20, 50, 100],
    movableColumns: true,
    placeholder: "No se encontraron datos disponibles",
  });

  tableInstance.on("tableBuilt", () => {
    updateRowCount();
  });
  tableInstance.on("dataFiltered", () => {
    updateRowCount();
  });
}

// Renderizar o actualizar el gráfico Chart.js
function renderChart() {
  const meta = manifest.indicators[activeIndicatorId];
  if (!meta || !meta.primary_metric) return;

  const ctx = document.getElementById("timeSeriesChart").getContext("2d");
  const metricCol = meta.primary_metric;

  // Filtrar según el rango de tiempo seleccionado
  let filteredData = [...currentData];
  const currentMaxYear = Math.max(...currentData.map(d => d.anio));

  if (chartRangeFilter === "10y") {
    filteredData = filteredData.filter(d => d.anio >= currentMaxYear - 10);
  } else if (chartRangeFilter === "5y") {
    filteredData = filteredData.filter(d => d.anio >= currentMaxYear - 5);
  }

  // Si hay categorías (e.g. departamentos), filtrar para el gráfico por Bolivia o agregado
  if (meta.category_column) {
    const catCol = meta.category_column;
    const hasBolivia = filteredData.some(d => String(d[catCol]).toUpperCase().includes("BOLIVIA"));
    if (hasBolivia) {
      filteredData = filteredData.filter(d => String(d[catCol]).toUpperCase().includes("BOLIVIA"));
    }
  }

  // Ordenar cronológicamente
  filteredData.sort((a, b) => {
    if (a.anio !== b.anio) return a.anio - b.anio;
    return (a.mes_num || 0) - (b.mes_num || 0);
  });

  const labels = filteredData.map(d => d.periodo || String(d.anio));
  const values = filteredData.map(d => d[metricCol]);

  if (chartInstance) {
    chartInstance.destroy();
  }

  const isBalanza = metricCol === "saldo_comercial_usd_millones";
  const bgColors = values.map(v => isBalanza ? (v >= 0 ? "rgba(16, 185, 129, 0.4)" : "rgba(239, 68, 68, 0.4)") : "rgba(16, 185, 129, 0.2)");
  const borderColors = values.map(v => isBalanza ? (v >= 0 ? "#10b981" : "#ef4444") : "#10b981");

  document.getElementById("chart-subtitle").innerText = `${meta.title} (${labels[0] || ""} a ${labels[labels.length - 1] || ""})`;

  chartInstance = new Chart(ctx, {
    type: isBalanza ? "bar" : "line",
    data: {
      labels: labels,
      datasets: [{
        label: meta.primary_metric_label || meta.title,
        data: values,
        borderColor: isBalanza ? borderColors : "#10b981",
        backgroundColor: bgColors,
        borderWidth: 2,
        pointRadius: labels.length > 80 ? 0 : 2,
        pointHoverRadius: 5,
        fill: !isBalanza,
        tension: 0.25
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: "index",
        intersect: false
      },
      plugins: {
        legend: {
          display: true,
          labels: { color: "#9ca3af", font: { family: "Inter", size: 12 } }
        },
        tooltip: {
          backgroundColor: "#1f2937",
          titleColor: "#f9fafb",
          bodyColor: "#10b981",
          borderColor: "#374151",
          borderWidth: 1,
          padding: 10,
          callbacks: {
            label: (ctx) => `${ctx.dataset.label}: ${Number(ctx.raw).toLocaleString("es-BO")} ${meta.unit || ""}`
          }
        }
      },
      scales: {
        x: {
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: { color: "#6b7280", maxTicksLimit: 12, font: { family: "Inter", size: 11 } }
        },
        y: {
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: {
            color: "#6b7280",
            font: { family: "JetBrains Mono", size: 11 },
            callback: (val) => `${Number(val).toLocaleString("es-BO")} ${meta.unit_short || ""}`
          }
        }
      }
    }
  });
}
