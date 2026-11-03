# Datos Bolivia - Plataforma Jamstack de Matrices Estadísticas Oficiales

Plataforma pre-compilada y estática para la visualización, auditoría y descarga de las matrices de datos económicos y sociales de Bolivia (PIB, Inflación acumulada, Balanza Comercial, Exportaciones, Importaciones, Tasa de Desocupación y Pobreza), obtenidas directamente del **Instituto Nacional de Estadística (INE)**: [https://www.ine.gob.bo/](https://www.ine.gob.bo/).

---

## ⚡ Requisito Crítico: 0 Cold Starts & Despliegue en Vercel Free Tier

1. **Cero Servidores Python en Producción:** Todo el procesamiento, limpieza de hojas de cálculo complejas y validación estadística ocurre **exclusivamente durante el build** (`python3 build.py`).
2. **Latencia Cero y 0s Cold Starts:** La web entregada a Vercel es 100% estática (`public/index.html`, assets CSS/JS y datos en `public/data/*.json` y `.csv`).
3. **Distribución Edge Global:** Los datos y la UI son cacheados en la red CDN de Vercel con cabeceras `Cache-Control: public, s-maxage=86400`, eliminando cualquier riesgo de suspensión por inactividad.

---

## 🏛️ Arquitectura del Sistema

```text
datos_bolivia/
├── data/
│   ├── raw/                       # Excels oficiales descargados del INE
│   │   ├── 01_pib_anual/
│   │   ├── 02_pib_trimestral/
│   │   ├── 03_inflacion_ipc/
│   │   ├── 05_exportaciones/
│   │   ├── 06_importaciones/
│   │   ├── 07_balanza_comercial/
│   │   ├── 08_pobreza_desigualdad/
│   │   ├── 09_tasa_desocupacion/
│   │   └── 10_igae/
│   └── metadata/                  # Catálogo de fuentes y hojas
├── pipeline/
│   ├── cleaners.py                # Parsers de Excels a DataFrames limpios (Tidy)
│   └── schemas.py                 # Esquemas Pandera (tipos, rangos, no-nulos)
├── templates/
│   └── index.html.j2              # Plantilla Jinja2 base
├── public/                        # Directorio estático final para Vercel
│   ├── index.html                 # HTML pre-renderizado con Jinja2
│   ├── style.css                  # UI moderna, modo oscuro ejecutivo y responsive
│   ├── app.js                     # Tabulator 5.6 + Chart.js + SheetJS (XLSX)
│   └── data/                      # Matrices estructuradas (.json y .csv)
│       ├── manifest.json          # Catálogo con KPIs pre-calculados
│       ├── balanza_comercial.json / .csv
│       ├── inflacion_ipc.json / .csv
│       ├── pib_anual.json / .csv
│       ├── pib_trimestral.json / .csv
│       ├── tasa_desocupacion.json / .csv
│       ├── pobreza_departamental.json / .csv
│       └── ...
├── validate_data.py               # Auditoría estricta de calidad (Pandera + Pytest)
├── build.py                       # Orquestador de validación, exportación y build HTML
├── vercel.json                    # Configuración oficial para Vercel
├── package.json                   # Scripts de automatización npm / Vercel
├── requirements.txt               # Dependencias Python mínimas
└── README.md
```

---

## 🛡️ Control de Calidad y Auditoría (`validate_data.py`)

El script de auditoría verifica rigurosamente:
1. **Esquemas Pandera:** Tipos de datos (`int`, `float`, `str`), ausencia de nulos en columnas críticas y rangos lógicos permitidos.
2. **Coherencia Temporal:** Series continuas año tras año sin saltos temporales ni huecos de información (PIB 1980-2024, IPC 1937-2026, Comercio Exterior 1992-2023, etc.).
3. **Sumatorias y Fórmulas Lógicas:**
   - **Balanza Comercial:** `Saldo Comercial == Exportaciones - Importaciones` (tolerancia de redondeo INE < $0.15M USD).
   - **Demografía y Pobreza:** La suma de la población de los 9 departamentos coincide exactamente con el total de Bolivia en todos los años.
   - **Límites de Empleo:** Tasas de desocupación urbana dentro de rangos macroeconómicos verosímiles.
4. **Aborto Seguro:** Si cualquier prueba falla, el script emite `sys.exit(1)` cancelando el build para evitar publicar datos corruptos.

---

## 💻 Ejecución Local

### 1. Configuración de dependencias
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Ejecutar auditoría de datos (Pandera / Pytest)
```bash
python3 validate_data.py
# o también con pytest:
pytest validate_data.py -v
```

### 3. Compilar el sitio estático
```bash
python3 build.py
```

### 4. Probar en servidor local
```bash
python3 -m http.server 8000 --directory public
```
Abre en tu navegador: `http://localhost:8000`

---

## 🚀 Despliegue en Vercel (Capa Gratuita)

1. Conecta tu repositorio de GitHub a [Vercel](https://vercel.com).
2. Vercel detectará automáticamente `vercel.json` y `package.json`.
3. Comando de build configurado: `pip install -r requirements.txt && python3 build.py`
4. Carpeta de salida (Output Directory): `public`
5. ¡Listo! Despliegue automático en Edge con 0 mantenimiento.

