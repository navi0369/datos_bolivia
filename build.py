#!/usr/bin/env python3
"""
Compilador Estático (Static Site Generator) para Despliegue en Vercel.
1. Ejecuta la auditoría estricta de calidad (validate_data.py).
2. Transforma y exporta los DataFrames a JSONs y CSVs estructurados en public/data/.
3. Inyecta metadatos y pre-renderiza public/index.html mediante Jinja2.
4. Garantiza 0 segundos de cold starts (cero servidores Python en producción).
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

# Metadatos descriptivos de los indicadores
INDICATORS_META = {
    "balanza_comercial": {
        "id": "balanza_comercial",
        "title": "Balanza Comercial (Exportaciones vs Importaciones)",
        "short_name": "Balanza Comercial",
        "category": "Sector Externo",
        "frequency": "Mensual",
        "icon": "⚖️",
        "description": "Evolución mensual del comercio exterior boliviano: Exportaciones FOB, Importaciones CIF y Saldo Comercial resultante (Superávit / Déficit) en millones de dólares.",
        "unit": "Millones USD",
        "unit_short": "M $US",
        "primary_metric": "saldo_comercial_usd_millones",
        "primary_metric_label": "Saldo Comercial (X - M)",
        "columns": [
            {"field": "periodo", "label": "Período", "type": "string"},
            {"field": "anio", "label": "Año", "type": "int"},
            {"field": "mes", "label": "Mes", "type": "string"},
            {"field": "exportaciones_usd_millones", "label": "Exportaciones ($US M)", "type": "float"},
            {"field": "importaciones_usd_millones", "label": "Importaciones ($US M)", "type": "float"},
            {"field": "saldo_comercial_usd_millones", "label": "Saldo Comercial ($US M)", "type": "float"},
        ]
    },
    "inflacion_ipc": {
        "id": "inflacion_ipc",
        "title": "Inflación Acumulada e Índice de Precios al Consumidor (IPC)",
        "short_name": "Inflación Acumulada (IPC)",
        "category": "Precios e Inflación",
        "frequency": "Mensual",
        "icon": "🏷️",
        "description": "Serie oficial empalmada nacional con base 2016=100. Incluye la variación acumulada anual (inflación oficial acumulada), variación mensual, variación interanual y nivel del índice.",
        "unit": "%",
        "unit_short": "%",
        "primary_metric": "inflacion_acumulada_pct",
        "primary_metric_label": "Inflación Acumulada (%)",
        "columns": [
            {"field": "periodo", "label": "Período", "type": "string"},
            {"field": "anio", "label": "Año", "type": "int"},
            {"field": "mes", "label": "Mes", "type": "string"},
            {"field": "inflacion_acumulada_pct", "label": "Inflación Acumulada (%)", "type": "float"},
            {"field": "inflacion_mensual_pct", "label": "Variación Mensual (%)", "type": "float"},
            {"field": "inflacion_12_meses_pct", "label": "Variación 12 Meses (%)", "type": "float"},
            {"field": "ipc_indice", "label": "Índice IPC", "type": "float"},
        ]
    },
    "pib_anual": {
        "id": "pib_anual",
        "title": "Producto Interno Bruto (PIB) Anual - Precios Constantes",
        "short_name": "PIB Anual",
        "category": "Cuentas Nacionales",
        "frequency": "Anual",
        "icon": "📈",
        "description": "Serie histórica oficial del PIB a precios constantes de 1990 desglosado por actividad económica (Agropecuaria, Minería, Hidrocarburos, Industria Manufacturera, Construcción, etc.).",
        "unit": "Miles Bs (1990)",
        "unit_short": "K Bs",
        "primary_metric": "pib_miles_bs_1990",
        "primary_metric_label": "PIB (Precios Constantes 1990)",
        "category_column": "actividad_economica",
        "columns": [
            {"field": "anio", "label": "Año", "type": "int"},
            {"field": "actividad_economica", "label": "Actividad Económica", "type": "string"},
            {"field": "pib_miles_bs_1990", "label": "Valor (Miles Bs 1990)", "type": "float"},
        ]
    },
    "pib_trimestral": {
        "id": "pib_trimestral",
        "title": "Producto Interno Bruto (PIB) Trimestral",
        "short_name": "PIB Trimestral",
        "category": "Cuentas Nacionales",
        "frequency": "Trimestral",
        "icon": "📊",
        "description": "Evolución trimestral de la actividad macroeconómica boliviana a precios constantes por sectores productivos.",
        "unit": "Miles Bs (1990)",
        "unit_short": "K Bs",
        "primary_metric": "pib_miles_bs_1990",
        "primary_metric_label": "PIB Trimestral",
        "category_column": "actividad_economica",
        "columns": [
            {"field": "periodo", "label": "Período", "type": "string"},
            {"field": "anio", "label": "Año", "type": "int"},
            {"field": "trimestre", "label": "Trimestre", "type": "string"},
            {"field": "actividad_economica", "label": "Actividad Económica", "type": "string"},
            {"field": "pib_miles_bs_1990", "label": "Valor (Miles Bs 1990)", "type": "float"},
        ]
    },
    "tasa_desocupacion": {
        "id": "tasa_desocupacion",
        "title": "Tasa de Desocupación Abierta en Área Urbana",
        "short_name": "Tasa de Desocupación",
        "category": "Mercado Laboral",
        "frequency": "Mensual",
        "icon": "👥",
        "description": "Tasa de desempleo urbano desestacionalizada proveniente de la Encuesta Continua de Empleo (ECE) del INE, desagregada por sexo.",
        "unit": "%",
        "unit_short": "%",
        "primary_metric": "tasa_desocupacion_total_pct",
        "primary_metric_label": "Tasa de Desocupación Total (%)",
        "columns": [
            {"field": "periodo", "label": "Período", "type": "string"},
            {"field": "anio", "label": "Año", "type": "int"},
            {"field": "mes", "label": "Mes", "type": "string"},
            {"field": "tasa_desocupacion_total_pct", "label": "Desocupación Total (%)", "type": "float"},
            {"field": "tasa_desocupacion_hombres_pct", "label": "Hombres (%)", "type": "float"},
            {"field": "tasa_desocupacion_mujeres_pct", "label": "Mujeres (%)", "type": "float"},
        ]
    },
    "pobreza_departamental": {
        "id": "pobreza_departamental",
        "title": "Indicadores de Pobreza Extrema Departamental",
        "short_name": "Pobreza Departamental",
        "category": "Pobreza y Condiciones Sociales",
        "frequency": "Anual",
        "icon": "🏘️",
        "description": "Población en situación de pobreza extrema e incidencia porcentual según departamento y total nacional (Encuesta de Hogares).",
        "unit": "%",
        "unit_short": "%",
        "primary_metric": "incidencia_pobreza_extrema_pct",
        "primary_metric_label": "Incidencia Pobreza Extrema (%)",
        "category_column": "departamento",
        "columns": [
            {"field": "anio", "label": "Año", "type": "int"},
            {"field": "departamento", "label": "Departamento", "type": "string"},
            {"field": "poblacion_total", "label": "Población Total", "type": "int"},
            {"field": "poblacion_pobreza_extrema", "label": "Pob. Pobreza Extrema", "type": "int"},
            {"field": "incidencia_pobreza_extrema_pct", "label": "Incidencia Pobreza (%)", "type": "float"},
        ]
    },
    "igae": {
        "id": "igae",
        "title": "Índice Global de Actividad Económica (IGAE)",
        "short_name": "IGAE Mensual",
        "category": "Cuentas Nacionales",
        "frequency": "Mensual",
        "icon": "⚡",
        "description": "Indicador mensual representativo del desempeño macroeconómico en el corto plazo (1990=100).",
        "unit": "Índice",
        "unit_short": "Pts",
        "primary_metric": "igae_indice",
        "primary_metric_label": "Índice IGAE",
        "columns": [
            {"field": "periodo", "label": "Período", "type": "string"},
            {"field": "anio", "label": "Año", "type": "int"},
            {"field": "mes", "label": "Mes", "type": "string"},
            {"field": "igae_indice", "label": "Índice IGAE", "type": "float"},
        ]
    },
    "exportaciones": {
        "id": "exportaciones",
        "title": "Exportaciones (X) por Actividad y Producto",
        "short_name": "Exportaciones (X)",
        "category": "Sector Externo",
        "frequency": "Anual",
        "icon": "🚢",
        "description": "Valor FOB en millones de dólares de exportaciones bolivianas según productos clave (Gas Natural, Zinc, Oro, Soja y derivados, Estaño, etc.).",
        "unit": "Millones USD",
        "unit_short": "M $US",
        "primary_metric": "valor_fob_usd_millones",
        "primary_metric_label": "Valor FOB Exportado",
        "category_column": "actividad_o_producto",
        "columns": [
            {"field": "anio", "label": "Año", "type": "int"},
            {"field": "actividad_o_producto", "label": "Actividad o Producto", "type": "string"},
            {"field": "valor_fob_usd_millones", "label": "Valor FOB ($US M)", "type": "float"},
        ]
    },
    "importaciones": {
        "id": "importaciones",
        "title": "Importaciones (M) Mensuales CIF",
        "short_name": "Importaciones (M)",
        "category": "Sector Externo",
        "frequency": "Mensual",
        "icon": "📦",
        "description": "Valor CIF mensual de las importaciones y volumen en peso bruto.",
        "unit": "Millones USD",
        "unit_short": "M $US",
        "primary_metric": "valor_cif_usd_millones",
        "primary_metric_label": "Importaciones CIF ($US M)",
        "columns": [
            {"field": "periodo", "label": "Período", "type": "string"},
            {"field": "anio", "label": "Año", "type": "int"},
            {"field": "mes", "label": "Mes", "type": "string"},
            {"field": "valor_cif_usd_millones", "label": "Valor CIF ($US M)", "type": "float"},
            {"field": "peso_bruto_kg", "label": "Peso Bruto (Kg)", "type": "int"},
        ]
    },
    "lineas_pobreza": {
        "id": "lineas_pobreza",
        "title": "Líneas de Pobreza y Pobreza Extrema Monetaria",
        "short_name": "Líneas de Pobreza (Bs)",
        "category": "Pobreza y Condiciones Sociales",
        "frequency": "Anual",
        "icon": "🥖",
        "description": "Valor monetario de las canastas básicas de consumo en Bolivianos por persona al mes según área y ciudad capital.",
        "unit": "Bs / persona / mes",
        "unit_short": "Bs",
        "primary_metric": "linea_pobreza_bs_mes",
        "primary_metric_label": "Línea de Pobreza (Bs/mes)",
        "category_column": "area_o_ciudad",
        "columns": [
            {"field": "anio", "label": "Año", "type": "int"},
            {"field": "periodo", "label": "Período", "type": "string"},
            {"field": "area_o_ciudad", "label": "Área o Ciudad", "type": "string"},
            {"field": "linea_pobreza_bs_mes", "label": "Línea Pobreza (Bs/mes)", "type": "float"},
        ]
    },
    "salario_medio_nominal": {
        "id": "salario_medio_nominal",
        "title": "Salario Medio Nominal del Sector Privado",
        "short_name": "Salario Medio Nominal",
        "category": "Mercado Laboral y Salarios",
        "frequency": "Anual",
        "icon": "💼",
        "description": "Índice de salario medio nominal de trabajadores del sector privado según grupo ocupacional (Gerentes, Profesionales, Empleados, Obreros).",
        "unit": "Índice (1995=100)",
        "unit_short": "Pts",
        "primary_metric": "indice_salario_nominal",
        "primary_metric_label": "Índice Salario Medio",
        "category_column": "grupo_ocupacional",
        "columns": [
            {"field": "anio", "label": "Año", "type": "int"},
            {"field": "grupo_ocupacional", "label": "Grupo Ocupacional", "type": "string"},
            {"field": "indice_salario_nominal", "label": "Índice Salario", "type": "float"},
        ]
    }
}


def compute_kpis(df: pd.DataFrame, meta: dict) -> dict:
    """Calcula estadísticas clave (KPIs) para renderizado instantáneo."""
    metric = meta.get("primary_metric")
    total_records = len(df)
    min_year = int(df["anio"].min())
    max_year = int(df["anio"].max())

    if metric and metric in df.columns:
        valid_df = df.dropna(subset=[metric]).copy()
        if "periodo" in valid_df.columns:
            latest_row = valid_df.sort_values(["anio", "mes_num" if "mes_num" in valid_df else "anio"]).iloc[-1]
            latest_date = str(latest_row.get("periodo", latest_row.get("anio")))
        else:
            latest_row = valid_df.sort_values("anio").iloc[-1]
            latest_date = str(latest_row.get("anio"))

        latest_val = float(latest_row[metric])

        # Min y Max
        min_idx = valid_df[metric].idxmin()
        max_idx = valid_df[metric].idxmax()
        min_row = valid_df.loc[min_idx]
        max_row = valid_df.loc[max_idx]

        min_val = float(min_row[metric])
        max_val = float(max_row[metric])
        min_date = str(min_row.get("periodo", min_row.get("anio")))
        max_date = str(max_row.get("periodo", max_row.get("anio")))

        return {
            "total_records": total_records,
            "min_year": min_year,
            "max_year": max_year,
            "latest_val": latest_val,
            "latest_val_formatted": f"{latest_val:,.2f}",
            "latest_date": latest_date,
            "max_val": max_val,
            "max_val_formatted": f"{max_val:,.2f}",
            "max_date": max_date,
            "min_val": min_val,
            "min_val_formatted": f"{min_val:,.2f}",
            "min_date": min_date
        }
    return {
        "total_records": total_records,
        "min_year": min_year,
        "max_year": max_year,
        "latest_val": None,
        "latest_val_formatted": "--",
        "latest_date": "--",
        "max_val": None,
        "max_val_formatted": "--",
        "max_date": "--",
        "min_val": None,
        "min_val_formatted": "--",
        "min_date": "--"
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
    indicators_list_for_template = []

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

        # Calcular KPIs
        kpis = compute_kpis(df, meta)

        ind_manifest = dict(meta)
        ind_manifest["min_year"] = kpis["min_year"]
        ind_manifest["max_year"] = kpis["max_year"]
        ind_manifest["kpis"] = kpis
        manifest_indicators[ind_id] = ind_manifest

        indicators_list_for_template.append({
            "id": ind_id,
            "title": meta["short_name"],
            "category": meta["category"],
            "frequency": meta["frequency"],
            "icon": meta["icon"]
        })

        logger.info(f"  ✓ Exportado '{ind_id}': {len(records):,} registros -> {json_path.name} y {csv_path.name}")

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

    rendered_html = template.render(
        indicators=indicators_list_for_template,
        build_timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
        total_indicators=len(indicators_list_for_template)
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
