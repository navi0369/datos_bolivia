#!/usr/bin/env python3
"""
Compilador Estático (Static Site Generator) para Despliegue en Vercel.
1. Ejecuta la auditoría estricta de calidad de datos (validate_data.py).
2. Transforma y exporta los DataFrames limpios a public/data/*.json y public/data/*.csv.
3. Inyecta metadatos oficiales y pre-renderiza public/index.html mediante Jinja2.
4. Cero dependencias de servidores Python en producción (100% Jamstack estático).
"""

import sys
import json
import logging
from datetime import datetime
from pathlib import Path
import pandas as pd
from jinja2 import Environment, FileSystemLoader

from pipeline.cleaners import load_all_clean_datasets
from validate_data import DataAuditor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("builder")

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"
PUBLIC_DATA_DIR = PUBLIC_DIR / "data"
TEMPLATES_DIR = BASE_DIR / "templates"

# Metadatos descriptivos completos y fuentes oficiales exactas del INE Bolivia
# Orden estricto dentro de cada categoría: 1. Anual -> 2. Trimestral -> 3. Mensual
INDICATORS_META = {
    # =========================================================================
    # SECCIÓN 1: CUENTAS NACIONALES Y ACTIVIDAD ECONÓMICA
    # =========================================================================
    "pib_anual": {
        "id": "pib_anual",
        "title": "Producto Interno Bruto (PIB) Anual a Precios Constantes",
        "short_name": "PIB Anual (Precios Constantes)",
        "category": "Cuentas Nacionales y Actividad",
        "frequency": "Anual",
        "icon": "🏛️",
        "description": "Serie histórica oficial del Producto Interno Bruto anual por actividad económica a precios constantes (Base 1990). Mide el volumen real producido por la economía boliviana sin distorsiones inflacionarias.",
        "official_table": "Cuadro Nº 06.01.01: Bolivia: Producto Interno Bruto a Precios Constantes de 1990, según tipo de actividad económica",
        "source_institution": "Instituto Nacional de Estadística (INE Bolivia)",
        "source_page": "https://www.ine.gob.bo/index.php/estadisticas-economicas/pib-y-cuentas-nacionales/producto-interno-bruto-anual/serie-historica-del-producto-interno-bruto/",
        "direct_url": "https://nube.ine.gob.bo/index.php/s/5HukXcuvSj76wKo/download",
        "source_filename": "pib_anual_precios_constantes_1980_2024.xlsx (Hoja: 06.01.01)",
        "methodology": "Sistema de Cuentas Nacionales (SCN-INE), Año Base 1990=100. Clasificación de Actividades Económicas de Bolivia (CAEB).",
        "unit": "Miles de Bolivianos de 1990",
        "unit_short": "Miles Bs (1990)",
        "category_column": "actividad_economica",
        "columns": [
            {"field": "anio", "label": "Año", "type": "int"},
            {"field": "actividad_economica", "label": "Actividad Económica", "type": "string"},
            {"field": "pib_miles_bs_1990", "label": "PIB Constante (Miles Bs 1990)", "type": "float"},
        ]
    },
    "pib_trimestral": {
        "id": "pib_trimestral",
        "title": "Producto Interno Bruto (PIB) Trimestral a Precios Constantes",
        "short_name": "PIB Trimestral",
        "category": "Cuentas Nacionales y Actividad",
        "frequency": "Trimestral",
        "icon": "📈",
        "description": "Desagregación trimestral del Producto Interno Bruto por tipo de actividad económica a precios constantes de 1990. Refleja la estacionalidad del crecimiento económico intra-anual.",
        "official_table": "Cuadro Nº 01.01.01: Bolivia: Producto Interno Bruto Trimestral a Precios Constantes, según actividad económica",
        "source_institution": "Instituto Nacional de Estadística (INE Bolivia)",
        "source_page": "https://www.ine.gob.bo/index.php/estadisticas-economicas/pib-y-cuentas-nacionales/producto-interno-bruto-trimestral/producto-interno-bruto-trimestral-intro/",
        "direct_url": "https://nimbus.ine.gob.bo/index.php/s/LgCGFBWiz2QccwP/download",
        "source_filename": "pib_trimestral_precios_constantes.xlsx (Hoja: 01.01.01)",
        "methodology": "Sistema de Cuentas Nacionales Trimestrales (SCNT-INE), Base 1990. Desglose no acumulado por trimestre calendario.",
        "unit": "Miles de Bolivianos de 1990",
        "unit_short": "Miles Bs (1990)",
        "category_column": "actividad_economica",
        "columns": [
            {"field": "periodo", "label": "Período (Año-Trimestre)", "type": "string"},
            {"field": "anio", "label": "Año", "type": "int"},
            {"field": "trimestre", "label": "Trimestre", "type": "string"},
            {"field": "actividad_economica", "label": "Actividad Económica", "type": "string"},
            {"field": "pib_miles_bs_1990", "label": "PIB Trimestral (Miles Bs 1990)", "type": "float"},
        ]
    },
    "igae": {
        "id": "igae",
        "title": "Índice Global de la Actividad Económica (IGAE)",
        "short_name": "IGAE Mensual",
        "category": "Cuentas Nacionales y Actividad",
        "frequency": "Mensual",
        "icon": "⏱️",
        "description": "Indicador cuantitativo sintético mensual que anticipa la dinámica macroeconómica agregada de la producción nacional en el corto plazo.",
        "official_table": "Cuadro Nº 01.02: Índice Global de la Actividad Económica (IGAE), por mes según año",
        "source_institution": "Instituto Nacional de Estadística (INE Bolivia)",
        "source_page": "https://www.ine.gob.bo/index.php/estadisticas-economicas/indice-global-de-actividad-economica-igae/",
        "direct_url": "https://nube.ine.gob.bo/index.php/s/6Szm6RmYSBeRnsD/download",
        "source_filename": "igae_mensual_y_acumulado_2008_2024.xlsx (Hoja: 01.02)",
        "methodology": "Cálculo sintético mensual de volumen de producción física ponderada, Base 1990=100.",
        "unit": "Puntos de Índice (1990=100)",
        "unit_short": "Pts",
        "columns": [
            {"field": "periodo", "label": "Período (Año-Mes)", "type": "string"},
            {"field": "anio", "label": "Año", "type": "int"},
            {"field": "mes", "label": "Mes", "type": "string"},
            {"field": "igae_indice", "label": "Índice IGAE (1990=100)", "type": "float"},
        ]
    },

    # =========================================================================
    # SECCIÓN 2: SECTOR EXTERNO Y COMERCIO EXTERIOR
    # =========================================================================
    "balanza_comercial_anual": {
        "id": "balanza_comercial_anual",
        "title": "Balanza Comercial Anual (Exportaciones FOB vs Importaciones CIF)",
        "short_name": "Balanza Comercial Anual",
        "category": "Sector Externo y Comercio",
        "frequency": "Anual",
        "icon": "⚖️",
        "description": "Consolidado anual de comercio exterior boliviano: Exportaciones totales FOB, Importaciones totales CIF y Saldo Comercial anual (Superávit o Déficit comercial) expresado en millones de dólares.",
        "official_table": "Bolivia: Balanza Comercial Anual - Exportaciones FOB, Importaciones CIF y Saldo Comercial",
        "source_institution": "Instituto Nacional de Estadística (INE Bolivia)",
        "source_page": "https://www.ine.gob.bo/index.php/estadisticas-economicas/comercio-exterior/saldo-comercial-cuadros-estadisticos/",
        "direct_url": "https://nube.ine.gob.bo/index.php/s/YmNagUYOHcty0fZ/download",
        "source_filename": "balanza_comercial_saldo_1992_2026.xlsx (Hoja: COMEX MENSUAL 92-26)",
        "methodology": "Manual de Balanza de Pagos del FMI (MBP6). Registros aduaneros consolidados anualmente.",
        "unit": "Millones USD",
        "unit_short": "M $US",
        "columns": [
            {"field": "anio", "label": "Año", "type": "int"},
            {"field": "exportaciones_usd_millones", "label": "Exportaciones FOB ($US M)", "type": "float"},
            {"field": "importaciones_usd_millones", "label": "Importaciones CIF ($US M)", "type": "float"},
            {"field": "saldo_comercial_usd_millones", "label": "Saldo Comercial Anual ($US M)", "type": "float"},
        ]
    },
    "exportaciones": {
        "id": "exportaciones",
        "title": "Exportaciones (X) Anuales por Actividad y Producto",
        "short_name": "Exportaciones por Producto",
        "category": "Sector Externo y Comercio",
        "frequency": "Anual",
        "icon": "🚢",
        "description": "Valor FOB anual de las exportaciones bolivianas desglosado por sector y producto principal (Gas Natural, Zinc, Oro, Soja y derivados, Estaño, Castaña, Plata, etc.).",
        "official_table": "Cuadro Nº 1: Bolivia: Exportaciones según Actividad Económica y Principales Productos (Valor FOB)",
        "source_institution": "Instituto Nacional de Estadística (INE Bolivia)",
        "source_page": "https://www.ine.gob.bo/index.php/estadisticas-economicas/comercio-exterior/cuadros-estadisticos-exportaciones/",
        "direct_url": "https://nube.ine.gob.bo/index.php/s/yJT9Q8KKyvhG4pi/download",
        "source_filename": "exportaciones_actividad_y_producto_1992_2026.xlsx (Hoja: ExpActProdAño 92-26 Valor)",
        "methodology": "Valor FOB (Free On Board) en millones de dólares. Documentos de Exportación (DEX) aduaneros procesados por el INE.",
        "unit": "Millones USD",
        "unit_short": "M $US",
        "category_column": "actividad_o_producto",
        "columns": [
            {"field": "anio", "label": "Año", "type": "int"},
            {"field": "actividad_o_producto", "label": "Actividad o Producto", "type": "string"},
            {"field": "valor_fob_usd_millones", "label": "Valor FOB ($US M)", "type": "float"},
        ]
    },
    "balanza_comercial": {
        "id": "balanza_comercial",
        "title": "Balanza Comercial Mensual (Saldo de Comercio Exterior)",
        "short_name": "Balanza Comercial Mensual",
        "category": "Sector Externo y Comercio",
        "frequency": "Mensual",
        "icon": "🔄",
        "description": "Evolución mensual del comercio exterior boliviano: Exportaciones FOB, Importaciones CIF y Saldo Comercial resultante (Superávit / Déficit) en millones de dólares.",
        "official_table": "Cuadro Nº 1: Bolivia: Saldo Comercial mensual según año y mes (Exportaciones FOB e Importaciones CIF)",
        "source_institution": "Instituto Nacional de Estadística (INE Bolivia)",
        "source_page": "https://www.ine.gob.bo/index.php/estadisticas-economicas/comercio-exterior/saldo-comercial-cuadros-estadisticos/",
        "direct_url": "https://nube.ine.gob.bo/index.php/s/YmNagUYOHcty0fZ/download",
        "source_filename": "balanza_comercial_saldo_1992_2026.xlsx (Hoja: COMEX MENSUAL 92-26)",
        "methodology": "Declaraciones Únicas de Importación (DUI/DIM) y Documentos de Exportación (DEX) aduaneros validados mensualmente por el INE.",
        "unit": "Millones USD",
        "unit_short": "M $US",
        "columns": [
            {"field": "periodo", "label": "Período (Año-Mes)", "type": "string"},
            {"field": "anio", "label": "Año", "type": "int"},
            {"field": "mes", "label": "Mes", "type": "string"},
            {"field": "exportaciones_usd_millones", "label": "Exportaciones ($US M)", "type": "float"},
            {"field": "importaciones_usd_millones", "label": "Importaciones ($US M)", "type": "float"},
            {"field": "saldo_comercial_usd_millones", "label": "Saldo Comercial ($US M)", "type": "float"},
        ]
    },
    "importaciones": {
        "id": "importaciones",
        "title": "Importaciones (M) Mensuales CIF y Volumen en Peso Bruto",
        "short_name": "Importaciones Mensuales",
        "category": "Sector Externo y Comercio",
        "frequency": "Mensual",
        "icon": "📦",
        "description": "Serie mensual de compras externas bolivianas registradas en valor CIF (millones de dólares) y volumen físico transportado en peso bruto (kilogramos).",
        "official_table": "Cuadro Nº 1: Bolivia: Importaciones por Año y Mes según Valor CIF y Volumen en Peso Bruto",
        "source_institution": "Instituto Nacional de Estadística (INE Bolivia)",
        "source_page": "https://www.ine.gob.bo/index.php/estadisticas-economicas/comercio-exterior/importaciones-cuadros-estadisticos/",
        "direct_url": "https://nube.ine.gob.bo/index.php/s/jYn9F8zMaAiAj3C/download",
        "source_filename": "importaciones_por_ano_y_mes_1992_2026.xlsx (Hoja: Importaciones_1992_2026)",
        "methodology": "Valor CIF (Cost, Insurance and Freight) en dólares estadounidenses y peso bruto aduanero en kilogramos.",
        "unit": "Millones USD / Kg",
        "unit_short": "M $US",
        "columns": [
            {"field": "periodo", "label": "Período (Año-Mes)", "type": "string"},
            {"field": "anio", "label": "Año", "type": "int"},
            {"field": "mes", "label": "Mes", "type": "string"},
            {"field": "valor_cif_usd_millones", "label": "Valor CIF ($US M)", "type": "float"},
            {"field": "peso_bruto_kg", "label": "Peso Bruto (Kg)", "type": "int"},
        ]
    },

    # =========================================================================
    # SECCIÓN 3: PRECIOS E INFLACIÓN
    # =========================================================================
    "inflacion_anual": {
        "id": "inflacion_anual",
        "title": "Inflación Oficial Anual Acumulada a Diciembre",
        "short_name": "Inflación Anual Oficial",
        "category": "Precios e Inflación",
        "frequency": "Anual",
        "icon": "📊",
        "description": "Tasa oficial histórica de inflación anual de Bolivia calculada al cierre del mes de diciembre de cada gestión fiscal sobre la serie empalmada del IPC.",
        "official_table": "Cuadro Nº 1.3: Bolivia: Índice de Precios al Consumidor - Variación Acumulada Anual (Inflación al cierre de gestión)",
        "source_institution": "Instituto Nacional de Estadística (INE Bolivia)",
        "source_page": "https://www.ine.gob.bo/index.php/serie-historica-empalmada/",
        "direct_url": "https://nube.ine.gob.bo/index.php/s/JZUH1mjiKSSURdN/download",
        "source_filename": "ipc_nacional_variacion_acumulada_mensual.xlsx (Hoja: CUADRO Nº 1.3 VAR ACUMULADA)",
        "methodology": "Serie Empalmada Nacional Oficial del IPC (Base 2016=100). Cierre anual fiscal al mes de diciembre.",
        "unit": "%",
        "unit_short": "%",
        "columns": [
            {"field": "anio", "label": "Año", "type": "int"},
            {"field": "inflacion_anual_pct", "label": "Inflación Anual Acumulada (%)", "type": "float"},
            {"field": "variacion_interanual_pct", "label": "Variación a 12 Meses (%)", "type": "float"},
            {"field": "ipc_indice", "label": "Nivel Índice IPC Diciembre", "type": "float"},
        ]
    },
    "inflacion_ipc": {
        "id": "inflacion_ipc",
        "title": "Inflación Mensual, Acumulada y Serie Empalmada del IPC",
        "short_name": "Inflación Acumulada e IPC",
        "category": "Precios e Inflación",
        "frequency": "Mensual",
        "icon": "🏷️",
        "description": "Serie oficial empalmada nacional con base 2016=100. Incluye la variación acumulada anual (inflación oficial acumulada), variación mensual, variación interanual y nivel del índice.",
        "official_table": "Serie Histórica Empalmada: Cuadros 1.1 (Índice), 1.2 (Var. Mensual), 1.3 (Var. Acumulada), 1.4 (Var. 12 Meses)",
        "source_institution": "Instituto Nacional de Estadística (INE Bolivia)",
        "source_page": "https://www.ine.gob.bo/index.php/serie-historica-empalmada/",
        "direct_url": "https://nube.ine.gob.bo/index.php/s/JZUH1mjiKSSURdN/download",
        "source_filename": "ipc_nacional_variacion_acumulada_mensual.xlsx (Hojas: CUADRO Nº 1.1, 1.2, 1.3, 1.4)",
        "methodology": "Índice de Precios al Consumidor (IPC), Base oficial 2016=100. Ponderaciones de canasta básica de consumo nacional urbano.",
        "unit": "% e Índice",
        "unit_short": "%",
        "columns": [
            {"field": "periodo", "label": "Período (Año-Mes)", "type": "string"},
            {"field": "anio", "label": "Año", "type": "int"},
            {"field": "mes", "label": "Mes", "type": "string"},
            {"field": "inflacion_acumulada_pct", "label": "Inflación Acumulada (%)", "type": "float"},
            {"field": "inflacion_mensual_pct", "label": "Variación Mensual (%)", "type": "float"},
            {"field": "inflacion_12_meses_pct", "label": "Variación 12 Meses (%)", "type": "float"},
            {"field": "ipc_indice", "label": "Nivel Índice IPC", "type": "float"},
        ]
    },

    # =========================================================================
    # SECCIÓN 4: POBREZA, EMPLEO Y MERCADO LABORAL
    # =========================================================================
    "pobreza_departamental": {
        "id": "pobreza_departamental",
        "title": "Pobreza Extrema e Incidencia Departamental",
        "short_name": "Pobreza Departamental",
        "category": "Pobreza y Mercado Laboral",
        "frequency": "Anual",
        "icon": "👥",
        "description": "Población total, población en condición de pobreza extrema y tasa de incidencia por departamento y para el total nacional de Bolivia.",
        "official_table": "Cuadro Nº 3.06.01.07: Bolivia: Población total, población en pobreza extrema e incidencia de pobreza extrema por departamento",
        "source_institution": "Instituto Nacional de Estadística (INE Bolivia)",
        "source_page": "https://www.ine.gob.bo/index.php/estadisticas-economicas/encuestas-de-hogares/",
        "direct_url": "https://nube.ine.gob.bo/index.php/s/PL0z2JpMaQtxt6o/download",
        "source_filename": "pobreza_incidencia_departamental_y_area.xlsx (Hoja: 3.06.01.07)",
        "methodology": "Encuesta de Hogares (EH - INE). Método de medición del costo de necesidades básicas (Línea de Pobreza).",
        "unit": "% y Personas",
        "unit_short": "%",
        "category_column": "departamento",
        "columns": [
            {"field": "anio", "label": "Año", "type": "int"},
            {"field": "departamento", "label": "Departamento / País", "type": "string"},
            {"field": "poblacion_total", "label": "Población Total", "type": "int"},
            {"field": "poblacion_pobreza_extrema", "label": "Población en Pobreza Extrema", "type": "int"},
            {"field": "incidencia_pobreza_extrema_pct", "label": "Incidencia Pobreza Extrema (%)", "type": "float"},
        ]
    },
    "lineas_pobreza": {
        "id": "lineas_pobreza",
        "title": "Líneas de Pobreza y Pobreza Extrema Monetaria",
        "short_name": "Líneas de Pobreza Monetaria",
        "category": "Pobreza y Mercado Laboral",
        "frequency": "Anual",
        "icon": "🥖",
        "description": "Valor monetario de las canastas básicas de consumo (Línea de Pobreza) y de consumo alimentario (Línea de Pobreza Extrema) expresado en Bolivianos por persona al mes según área y ciudad capital.",
        "official_table": "Cuadro Nº 3.06.01.05: Bolivia: Líneas de Pobreza Moderada y Pobreza Extrema según Área Geográfica y Ciudad Capital",
        "source_institution": "Instituto Nacional de Estadística (INE Bolivia)",
        "source_page": "https://www.ine.gob.bo/index.php/estadisticas-economicas/encuestas-de-hogares/",
        "direct_url": "https://nube.ine.gob.bo/index.php/s/9fxl3w1m1sM6hFm/download",
        "source_filename": "lineas_de_pobreza_monetaria_bs.xlsx (Hoja: 3.06.01.05)",
        "methodology": "Canasta Básica de Alimentos (CBA para indigencia) y Canasta Básica Total (CBT para pobreza) calculadas por el INE.",
        "unit": "Bs / persona / mes",
        "unit_short": "Bs/mes",
        "category_column": "area_o_ciudad",
        "columns": [
            {"field": "anio", "label": "Año", "type": "int"},
            {"field": "periodo", "label": "Período", "type": "string"},
            {"field": "area_o_ciudad", "label": "Área o Ciudad", "type": "string"},
            {"field": "linea_pobreza_bs_mes", "label": "Línea Pobreza (Bs/persona/mes)", "type": "float"},
        ]
    },
    "salario_medio_nominal": {
        "id": "salario_medio_nominal",
        "title": "Salario Medio Nominal del Sector Privado por Ocupación",
        "short_name": "Salario Medio Nominal Privado",
        "category": "Pobreza y Mercado Laboral",
        "frequency": "Anual",
        "icon": "💼",
        "description": "Índice de salario medio nominal de trabajadores asalariados del sector privado boliviano clasificado por grupo ocupacional (Gerentes, Profesionales, Empleados, Obreros).",
        "official_table": "Cuadro: Bolivia: Índice de Salario Medio Nominal del Sector Privado por Grupo Ocupacional",
        "source_institution": "Instituto Nacional de Estadística (INE Bolivia)",
        "source_page": "https://www.ine.gob.bo/index.php/estadisticas-economicas/salarios-renumeraciones-y-empleo-de-los-asalariados-en-el-sector-privado-cuadros-estadisticos/",
        "direct_url": "https://nube.ine.gob.bo/index.php/s/7QNGChZRzw8mXRV/download",
        "source_filename": "salario_medio_nominal_sector_privado.xlsx (Hoja: INDICE-NOMINAL-OCUPACION)",
        "methodology": "Encuesta de Salarios y Remuneraciones del Sector Privado, Año Base 1995=100.",
        "unit": "Puntos de Índice (1995=100)",
        "unit_short": "Pts",
        "category_column": "grupo_ocupacional",
        "columns": [
            {"field": "anio", "label": "Año", "type": "int"},
            {"field": "grupo_ocupacional", "label": "Grupo Ocupacional", "type": "string"},
            {"field": "indice_salario_nominal", "label": "Índice Salario Nominal", "type": "float"},
        ]
    },
    "tasa_desocupacion": {
        "id": "tasa_desocupacion",
        "title": "Tasa de Desocupación Urbana Desestacionalizada",
        "short_name": "Tasa de Desocupación Urbana",
        "category": "Pobreza y Mercado Laboral",
        "frequency": "Mensual",
        "icon": "👔",
        "description": "Porcentaje de la Población Económicamente Activa (PEA) desocupada en el área urbana de Bolivia, con ajuste estacional y desagregación por sexo.",
        "official_table": "Cuadro Nº 3.05.01.13: Bolivia: Área Urbana - Tasa de Desocupación Desestacionalizada por Mes, según Sexo",
        "source_institution": "Instituto Nacional de Estadística (INE Bolivia)",
        "source_page": "https://www.ine.gob.bo/index.php/estadisticas-sociales/bolivia-area-urbana-tasa-de-desocupacion-desestacionalizada/",
        "direct_url": "https://nube.ine.gob.bo/index.php/s/5TvMscznkP1SxvQ/download",
        "source_filename": "tasa_desocupacion_urbana_2015_2026.xlsx (Hoja: 3.05.01.13)",
        "methodology": "Encuesta Continua de Empleo (ECE - INE). Serie desestacionalizada mediante modelo estadístico X-13ARIMA-SEATS.",
        "unit": "%",
        "unit_short": "%",
        "columns": [
            {"field": "periodo", "label": "Período (Año-Mes)", "type": "string"},
            {"field": "anio", "label": "Año", "type": "int"},
            {"field": "mes", "label": "Mes", "type": "string"},
            {"field": "tasa_desocupacion_total_pct", "label": "Tasa Total (%)", "type": "float"},
            {"field": "tasa_desocupacion_hombres_pct", "label": "Hombres (%)", "type": "float"},
            {"field": "tasa_desocupacion_mujeres_pct", "label": "Mujeres (%)", "type": "float"},
        ]
    }
}


def build():
    print("=" * 80)
    print(" ETAPA DE COMPILACIÓN ESTÁTICA PARA VERCEL (BUILD PIPELINE)")
    print("=" * 80)

    # 1. Ejecutar auditoría y control de calidad estricto
    logger.info("Paso 1: Iniciando auditoría de calidad de datos...")
    datasets = load_all_clean_datasets()
    auditor = DataAuditor(datasets)
    audit_passed = auditor.run_all()

    if not audit_passed:
        logger.error("La auditoría de calidad falló. Abortando compilación y despliegue.")
        sys.exit(1)

    logger.info("Paso 1 completado: Auditoría superada con éxito (Exit Code 0).")

    # 2. Preparar directorios estáticos
    PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)

    manifest_indicators = {}
    grouped_indicators = {}

    # 3. Exportar datasets a JSON y CSV en public/data/
    logger.info("Paso 2: Exportando matrices a public/data/*.json y public/data/*.csv...")

    for ind_id, meta in INDICATORS_META.items():
        if ind_id not in datasets:
            logger.warning(f"Dataset '{ind_id}' no encontrado en datasets limpios.")
            continue

        df = datasets[ind_id]
        json_path = PUBLIC_DATA_DIR / f"{ind_id}.json"
        csv_path = PUBLIC_DATA_DIR / f"{ind_id}.csv"

        # Guardar CSV
        df.to_csv(csv_path, index=False, encoding="utf-8")

        # Guardar JSON estructurado
        records = df.to_dict(orient="records")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False)

        min_year = int(df["anio"].min())
        max_year = int(df["anio"].max())
        total_records = len(df)

        ind_manifest = dict(meta)
        ind_manifest["min_year"] = min_year
        ind_manifest["max_year"] = max_year
        ind_manifest["total_records"] = total_records
        manifest_indicators[ind_id] = ind_manifest

        # Agrupar por categoría preservando el orden estricto (Anual -> Trimestral -> Mensual)
        cat = meta["category"]
        if cat not in grouped_indicators:
            grouped_indicators[cat] = []

        grouped_indicators[cat].append({
            "id": ind_id,
            "title": meta["title"],
            "short_name": meta["short_name"],
            "category": meta["category"],
            "frequency": meta["frequency"],
            "icon": meta["icon"],
            "min_year": min_year,
            "max_year": max_year,
            "total_records": total_records
        })

        logger.info(f"  ✓ Exportado '{ind_id}': {len(records):,} registros [{min_year}-{max_year}] -> {json_path.name} y {csv_path.name}")

    # Guardar catálogo global (manifest.json)
    manifest_path = PUBLIC_DATA_DIR / "manifest.json"
    manifest_data = {
        "portal": "Datos Bolivia - Plataforma Oficial de Indicadores",
        "generated_at": datetime.now().isoformat(),
        "total_indicators": len(manifest_indicators),
        "indicators": manifest_indicators
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2, ensure_ascii=False)
    logger.info(f"  ✓ Manifiesto global exportado a: {manifest_path.name}")

    # 4. Compilar plantilla Jinja2 a public/index.html
    logger.info("Paso 3: Compilando plantilla HTML estática con Jinja2...")
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("index.html.j2")

    # Obtener el ID del primer indicador para marcarlo activo inicialmente
    first_indicator_id = list(manifest_indicators.keys())[0] if manifest_indicators else ""

    rendered_html = template.render(
        grouped_indicators=grouped_indicators,
        first_indicator_id=first_indicator_id,
        build_timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
        total_indicators=len(manifest_indicators)
    )

    output_html_path = PUBLIC_DIR / "index.html"
    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(rendered_html)

    logger.info(f"  ✓ Archivo estático generado en: {output_html_path}")

    print("\n" + "=" * 80)
    print(" ✅ COMPILACIÓN COMPLETADA EXITOSAMENTE")
    print(f" Sitio web estático listo para Vercel en: {PUBLIC_DIR}")
    print("=" * 80)


if __name__ == "__main__":
    build()
