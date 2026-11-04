/**
 * Aplicación cliente de visualización y exploración de datos del INE Bolivia.
 * 100% Client-side: Tabulator + SheetJS (Sin Chart.js, sin gráficos, solo matrices limpias).
 */

let manifest = null;
let activeIndicatorId = null;
let currentData = [];
let tableInstance = null;

// Inicialización cuando el DOM esté listo
document.addEventListener("DOMContentLoaded", async () => {
  await loadManifest();
  setupEventListeners();
});

// Cargar catálogo de indicadores pre-compilado en manifest.json
async function loadManifest() {
  try {
    const res = await fetch("data/manifest.json");
    if (!res.ok) throw new Error("No se pudo cargar el catálogo manifest.json");
    manifest = await res.json();

    // Seleccionar primer indicador disponible por defecto
    const firstInd = Object.keys(manifest.indicators)[0];
    if (firstInd) {
      switchIndicator(firstInd);
    }
  } catch (err) {
    console.error("Error al inicializar la aplicación:", err);
    const titleEl = document.getElementById("ind-title");
    const descEl = document.getElementById("ind-description");
    if (titleEl) titleEl.innerText = "Error cargando datos";
    if (descEl) descEl.innerText = err.message;
  }
}

// Configurar escuchadores de eventos
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

  // Filtro de búsqueda en tiempo real
  const searchInput = document.getElementById("table-search");
  if (searchInput) {
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
  }

  // Filtro desplegable por Año
  const yearSelect = document.getElementById("filter-year");
  if (yearSelect) {
    yearSelect.addEventListener("change", applyFilters);
  }

  // Filtro desplegable por Variable secundaria
  const varSelect = document.getElementById("filter-variable");
  if (varSelect) {
    varSelect.addEventListener("change", applyFilters);
  }

  // Botón Exportar CSV
  const btnCsv = document.getElementById("btn-export-csv");
  if (btnCsv) {
    btnCsv.addEventListener("click", () => {
      if (!tableInstance) return;
      tableInstance.download("csv", `${activeIndicatorId}_ine_bolivia.csv`);
    });
  }

  // Botón Exportar Excel (.xlsx)
  const btnXlsx = document.getElementById("btn-export-xlsx");
  if (btnXlsx) {
    btnXlsx.addEventListener("click", () => {
      if (!tableInstance) return;
      tableInstance.download("xlsx", `${activeIndicatorId}_ine_bolivia.xlsx`, {
        sheetName: "Datos INE Bolivia"
      });
    });
  }
}

// Cambiar matriz/indicador activo
async function switchIndicator(indId) {
  activeIndicatorId = indId;
  const meta = manifest.indicators[indId];
  if (!meta) return;

  // Actualizar estado activo en la barra lateral
  document.querySelectorAll(".nav-btn").forEach(btn => {
    btn.classList.toggle("active", btn.getAttribute("data-indicator-id") === indId);
  });

  // 1. Actualizar Ficha Técnica y Fuente Exacta
  document.getElementById("ind-title").innerText = meta.title;
  document.getElementById("ind-description").innerText = meta.description;

  const catPill = document.getElementById("src-category-pill");
  if (catPill) catPill.innerText = meta.category;

  const freqPill = document.getElementById("src-frequency-pill");
  if (freqPill) {
    freqPill.innerText = meta.frequency.toUpperCase();
    freqPill.className = `pill pill-freq freq-${meta.frequency.toLowerCase()}`;
  }

  // Enlaces oficiales directos
  const pageLink = document.getElementById("btn-src-page");
  if (pageLink) {
    pageLink.href = meta.source_page || "#";
    pageLink.target = "_blank";
  }

  const dlLink = document.getElementById("btn-src-download");
  if (dlLink) {
    dlLink.href = meta.direct_url || "#";
    dlLink.target = "_blank";
  }

  // Campos de detalle de la fuente
  const tableNameEl = document.getElementById("src-table-name");
  if (tableNameEl) tableNameEl.innerText = meta.official_table || meta.title;

  const fileNameEl = document.getElementById("src-file-name");
  if (fileNameEl) fileNameEl.innerText = meta.source_filename || "--";

  const methEl = document.getElementById("src-methodology");
  if (methEl) methEl.innerText = meta.methodology || "--";

  const covEl = document.getElementById("src-coverage");
  if (covEl) {
    const totalRecs = meta.total_records ? meta.total_records.toLocaleString("es-BO") : "--";
    covEl.innerText = `${meta.min_year} - ${meta.max_year} (${totalRecs} registros)`;
  }

  const unitEl = document.getElementById("src-unit");
  if (unitEl) unitEl.innerText = meta.unit || "--";

  // 2. Cargar datos del JSON estático compilado
  try {
    const res = await fetch(`data/${indId}.json`);
    if (!res.ok) throw new Error(`No se pudo cargar el archivo data/${indId}.json`);
    currentData = await res.json();

    populateFilterDropdowns(meta);
    renderTable(meta);
  } catch (err) {
    console.error("Error al cargar la matriz de datos:", err);
  }
}

// Llenar selectores de filtro con los datos actuales
function populateFilterDropdowns(meta) {
  // Filtro de Año
  const yearSelect = document.getElementById("filter-year");
  if (yearSelect) {
    yearSelect.innerHTML = '<option value="">Todos los años</option>';
    const years = [...new Set(currentData.map(d => d.anio))].filter(Boolean).sort((a, b) => b - a);
    years.forEach(y => {
      const opt = document.createElement("option");
      opt.value = y;
      opt.textContent = y;
      yearSelect.appendChild(opt);
    });
  }

  // Filtro de variable secundaria (e.g. actividad_economica, departamento, etc.)
  const varContainer = document.getElementById("variable-filter-container");
  const varSelect = document.getElementById("filter-variable");
  const varKey = meta.category_column;

  if (varKey && currentData.length > 0 && currentData[0][varKey] !== undefined) {
    varContainer.style.display = "flex";
    varSelect.innerHTML = '<option value="">Todas</option>';
    const distinctVars = [...new Set(currentData.map(d => d[varKey]))].filter(Boolean).sort();
    distinctVars.forEach(v => {
      const opt = document.createElement("option");
      opt.value = v;
      opt.textContent = v;
      varSelect.appendChild(opt);
    });
  } else {
    varContainer.style.display = "none";
  }

  const searchInput = document.getElementById("table-search");
  if (searchInput) searchInput.value = "";
}

// Aplicar filtros combinados (año y variable secundaria)
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

// Actualizar el contador de filas filtradas/activas
function updateRowCount() {
  setTimeout(() => {
    if (tableInstance) {
      const count = tableInstance.getDataCount("active");
      const el = document.getElementById("table-row-count");
      if (el) {
        el.innerText = `${count.toLocaleString("es-BO")} registros encontrados`;
      }
    }
  }, 50);
}

// Renderizar la tabla con Tabulator
function renderTable(meta) {
  const columns = meta.columns.map(col => {
    const isNum = col.type === "number" || col.type === "float" || col.type === "int";
    return {
      title: col.label,
      field: col.field,
      sorter: isNum ? "number" : "string",
      hozAlign: isNum ? "right" : "left",
      headerHozAlign: isNum ? "right" : "left",
      formatter: isNum ? (cell) => {
        const val = cell.getValue();
        if (val === null || val === undefined) return '<span class="text-muted">-</span>';
        // Formatear decimales si no es entero
        const maxDec = col.type === "int" ? 0 : 2;
        return `<span class="font-mono">${Number(val).toLocaleString("es-BO", { maximumFractionDigits: maxDec, minimumFractionDigits: col.type === "int" ? 0 : 2 })}</span>`;
      } : (cell) => {
        const val = cell.getValue();
        return val ? String(val) : '<span class="text-muted">-</span>';
      }
    };
  });

  tableInstance = new Tabulator("#data-table", {
    data: currentData,
    columns: columns,
    layout: "fitColumns",
    responsiveLayout: "collapse",
    pagination: "local",
    paginationSize: 25,
    paginationSizeSelector: [15, 25, 50, 100, 500],
    movableColumns: true,
    placeholder: "No se encontraron registros para los filtros seleccionados",
  });

  tableInstance.on("tableBuilt", () => {
    updateRowCount();
  });
  tableInstance.on("dataFiltered", () => {
    updateRowCount();
  });
}
