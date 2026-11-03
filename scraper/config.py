"""
Configuración de indicadores clave del Instituto Nacional de Estadística (INE) de Bolivia.
Define las fuentes oficiales, páginas de origen en www.ine.gob.bo y enlaces de descarga.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
METADATA_DIR = DATA_DIR / "metadata"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}

INDICATORS = [
    {
        "id": "01_pib_anual",
        "name": "Producto Interno Bruto (PIB) Anual - Precios Constantes",
        "category": "Cuentas Nacionales",
        "frequency": "Anual",
        "description": "Serie histórica del PIB a precios constantes por año según tipo de actividad económica (1980 - 2024).",
        "source_page": "https://www.ine.gob.bo/index.php/estadisticas-economicas/pib-y-cuentas-nacionales/producto-interno-bruto-anual/serie-historica-del-producto-interno-bruto/",
        "direct_url": "https://nube.ine.gob.bo/index.php/s/5HukXcuvSj76wKo/download",
        "link_pattern": r"CONSTANTES.*ACTIVIDAD",
        "canonical_filename": "pib_anual_precios_constantes_1980_2024.xlsx"
    },
    {
        "id": "02_pib_trimestral",
        "name": "Producto Interno Bruto (PIB) Trimestral",
        "category": "Cuentas Nacionales",
        "frequency": "Trimestral",
        "description": "PIB a precios de mercado y constantes por actividad económica por trimestre.",
        "source_page": "https://www.ine.gob.bo/index.php/estadisticas-economicas/pib-y-cuentas-nacionales/producto-interno-bruto-trimestral/producto-interno-bruto-trimestral-intro/",
        "direct_url": "https://nimbus.ine.gob.bo/index.php/s/LgCGFBWiz2QccwP/download",
        "link_pattern": r"PRODUCTO INTERNO BRUTO A PRECIOS CONSTANTES",
        "canonical_filename": "pib_trimestral_precios_constantes.xlsx"
    },
    {
        "id": "03_inflacion_ipc",
        "name": "Índice de Precios al Consumidor (IPC) e Inflación Acumulada",
        "category": "Precios e Inflación",
        "frequency": "Mensual",
        "description": "Serie empalmada nacional oficial: Índice general, variación mensual, acumulada (inflación acumulada) y a 12 meses.",
        "source_page": "https://www.ine.gob.bo/index.php/serie-historica-empalmada/",
        "direct_url": "https://nube.ine.gob.bo/index.php/s/JZUH1mjiKSSURdN/download",
        "link_pattern": r"Índice General, Variación Mensual, Acumulada y a 12 Meses",
        "canonical_filename": "ipc_nacional_variacion_acumulada_mensual.xlsx"
    },
    {
        "id": "04_inflacion_ipc_division",
        "name": "IPC e Inflación por División de Gasto (Canasta de Bienes)",
        "category": "Precios e Inflación",
        "frequency": "Mensual",
        "description": "Índice general y variaciones mensual, acumulada y a 12 meses desglosado por división de gasto (Alimentos, Transporte, Vivienda, Salud, etc.).",
        "source_page": "https://www.ine.gob.bo/index.php/serie-historica-empalmada/",
        "direct_url": "https://nube.ine.gob.bo/index.php/s/cgXaupaB4Twheqg/download",
        "link_pattern": r"por División",
        "canonical_filename": "ipc_por_division_de_gasto.xlsx"
    },
    {
        "id": "05_exportaciones",
        "name": "Exportaciones (X) según Actividad Económica y Producto",
        "category": "Sector Externo",
        "frequency": "Mensual / Anual",
        "description": "Exportaciones bolivianas valor FOB según actividad económica y grandes productos (Gas natural, minerales, agroindustria) 1992 - 2026.",
        "source_page": "https://www.ine.gob.bo/index.php/estadisticas-economicas/comercio-exterior/cuadros-estadisticos-exportaciones/",
        "direct_url": "https://nube.ine.gob.bo/index.php/s/yJT9Q8KKyvhG4pi/download",
        "link_pattern": r"Actividad Económica y Producto",
        "canonical_filename": "exportaciones_actividad_y_producto_1992_2026.xlsx"
    },
    {
        "id": "06_importaciones",
        "name": "Importaciones (M) por Año y Mes",
        "category": "Sector Externo",
        "frequency": "Mensual / Anual",
        "description": "Importaciones bolivianas valor CIF según año y mes (1992 - 2026) y grandes categorías.",
        "source_page": "https://www.ine.gob.bo/index.php/estadisticas-economicas/comercio-exterior/importaciones-cuadros-estadisticos/",
        "direct_url": "https://nube.ine.gob.bo/index.php/s/jYn9F8zMaAiAj3C/download",
        "link_pattern": r"Importaciones por Año y Mes",
        "canonical_filename": "importaciones_por_ano_y_mes_1992_2026.xlsx"
    },
    {
        "id": "07_balanza_comercial",
        "name": "Balanza Comercial (Saldo Comercial: X - M)",
        "category": "Sector Externo",
        "frequency": "Mensual / Anual",
        "description": "Evolución histórica del comercio exterior boliviano: Exportaciones, Importaciones y Saldo Comercial (superávit / déficit) 1992 - 2026.",
        "source_page": "https://www.ine.gob.bo/index.php/estadisticas-economicas/comercio-exterior/saldo-comercial-cuadros-estadisticos/",
        "direct_url": "https://nube.ine.gob.bo/index.php/s/YmNagUYOHcty0fZ/download",
        "link_pattern": r"Comercio Exterior según Año y Mes",
        "canonical_filename": "balanza_comercial_saldo_1992_2026.xlsx"
    },
    {
        "id": "08_pobreza_desigualdad",
        "name": "Indicadores de Pobreza Moderada y Extrema",
        "category": "Pobreza y Condiciones Sociales",
        "frequency": "Anual",
        "description": "Incidencia de pobreza moderada y pobreza extrema según departamento y área geográfica (urbana / rural) de la Encuesta de Hogares.",
        "source_page": "https://www.ine.gob.bo/index.php/estadisticas-economicas/encuestas-de-hogares/",
        "direct_url": "https://nube.ine.gob.bo/index.php/s/PL0z2JpMaQtxt6o/download",
        "link_pattern": r"INCIDENCIA DE POBREZA.*DEPARTAMENTO",
        "canonical_filename": "pobreza_incidencia_departamental_y_area.xlsx"
    },
    {
        "id": "09_tasa_desocupacion",
        "name": "Tasa de Desocupación Urbana (Empleo / Desempleo)",
        "category": "Mercado Laboral",
        "frequency": "Mensual / Trimestral",
        "description": "Tasa de desocupación urbana desestacionalizada por mes según sexo (Encuesta Continua de Empleo - ECE 2015 - 2026).",
        "source_page": "https://www.ine.gob.bo/index.php/estadisticas-sociales/bolivia-area-urbana-tasa-de-desocupacion-desestacionalizada/",
        "direct_url": "https://nube.ine.gob.bo/index.php/s/5TvMscznkP1SxvQ/download",
        "link_pattern": r"Tasa de desocupación desestacionalizada",
        "canonical_filename": "tasa_desocupacion_urbana_2015_2026.xlsx"
    },
    {
        "id": "10_igae",
        "name": "Índice Global de Actividad Económica (IGAE)",
        "category": "Cuentas Nacionales",
        "frequency": "Mensual",
        "description": "Indicador mensual del desempeño de la actividad económica general de Bolivia y variación acumulada (2008 - 2024).",
        "source_page": "https://www.ine.gob.bo/index.php/estadisticas-economicas/indice-global-de-actividad-economica-igae/",
        "direct_url": "https://nube.ine.gob.bo/index.php/s/6Szm6RmYSBeRnsD/download",
        "link_pattern": r"INDICE GLOBAL DE LA ACTIVIDAD ECONÓMICA, POR MES",
        "canonical_filename": "igae_mensual_y_acumulado_2008_2024.xlsx"
    },
    {
        "id": "11_lineas_pobreza",
        "name": "Líneas de Pobreza y Pobreza Extrema Monetaria",
        "category": "Pobreza y Condiciones Sociales",
        "frequency": "Anual",
        "description": "Valor monetario de las canastas básicas de consumo (Línea de Pobreza) y alimentaria (Línea de Pobreza Extrema) en Bs por persona/mes.",
        "source_page": "https://www.ine.gob.bo/index.php/estadisticas-economicas/encuestas-de-hogares/",
        "direct_url": "https://nube.ine.gob.bo/index.php/s/9fxl3w1m1sM6hFm/download",
        "link_pattern": r"LÍNEAS DE POBREZA Y POBREZA EXTREMA",
        "canonical_filename": "lineas_de_pobreza_monetaria_bs.xlsx"
    },
    {
        "id": "12_salario_medio_nominal",
        "name": "Salario Medio Nominal del Sector Privado",
        "category": "Mercado Laboral y Salarios",
        "frequency": "Trimestral / Anual",
        "description": "Salario medio nominal de trabajadores asalariados del sector privado por grupo ocupacional (1996 - 2023).",
        "source_page": "https://www.ine.gob.bo/index.php/estadisticas-economicas/salarios-renumeraciones-y-empleo-de-los-asalariados-en-el-sector-privado-cuadros-estadisticos/",
        "direct_url": "https://nube.ine.gob.bo/index.php/s/7QNGChZRzw8mXRV/download",
        "link_pattern": r"Salario Medio Nominal.*Grupo Ocupacional",
        "canonical_filename": "salario_medio_nominal_sector_privado.xlsx"
    }
]
