"""
Módulo de transformación y estandarización de Excels oficiales del INE a DataFrames limpios (Tidy Data).
"""

from pathlib import Path
from typing import Dict, Optional, List, Any
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"

MESES_ES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
    'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12,
    'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12
}


def parse_year_value(val) -> Optional[int]:
    """Extrae un año de 4 dígitos de strings como '2017(p)', '2024(p)', 2020, etc."""
    if val is None or pd.isna(val) or val == 0:
        return None
    s = str(val).strip()
    digits = "".join(ch for ch in s if ch.isdigit())
    if len(digits) >= 4:
        candidate = int(digits[:4])
        if 1900 <= candidate <= 2035:
            return candidate
    return None


def clean_balanza_comercial() -> pd.DataFrame:
    """Procesa el saldo de comercio exterior mensual (1992-2026): Exportaciones, Importaciones, Saldo."""
    path = RAW_DIR / "07_balanza_comercial/balanza_comercial_saldo_1992_2026.xlsx"
    df = pd.read_excel(path, sheet_name="COMEX MENSUAL 92-26", skiprows=3)
    df = df[["Año", "Mes ", "Exportaciones", "Importaciones(2)", "Saldo Comercial"]].copy()

    df["Año"] = pd.to_numeric(df["Año"], errors="coerce")
    df["Año"] = df["Año"].ffill()
    df = df.dropna(subset=["Exportaciones", "Importaciones(2)", "Saldo Comercial"])

    df["Mes "] = df["Mes "].astype(str).str.strip()
    df = df[~df["Mes "].str.lower().str.contains("total|fuente|nota|p/|^nan$")]

    df = df.rename(columns={
        "Año": "anio",
        "Mes ": "mes",
        "Exportaciones": "exportaciones_usd_millones",
        "Importaciones(2)": "importaciones_usd_millones",
        "Saldo Comercial": "saldo_comercial_usd_millones"
    })

    df["anio"] = df["anio"].astype(int)
    for col in ["exportaciones_usd_millones", "importaciones_usd_millones", "saldo_comercial_usd_millones"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").round(2)

    df["mes_num"] = df["mes"].str.lower().map(MESES_ES)
    df["periodo"] = df["anio"].astype(str) + "-" + df["mes_num"].astype(str).str.zfill(2)
    df = df.sort_values(["anio", "mes_num"]).reset_index(drop=True)
    return df


def clean_balanza_comercial_anual() -> pd.DataFrame:
    """Procesa el saldo de comercio exterior anual (1992-2023) consolidado por año."""
    df_m = clean_balanza_comercial()
    grp = df_m.groupby("anio").agg({
        "exportaciones_usd_millones": "sum",
        "importaciones_usd_millones": "sum"
    }).reset_index()

    grp["exportaciones_usd_millones"] = grp["exportaciones_usd_millones"].round(2)
    grp["importaciones_usd_millones"] = grp["importaciones_usd_millones"].round(2)
    grp["saldo_comercial_usd_millones"] = (grp["exportaciones_usd_millones"] - grp["importaciones_usd_millones"]).round(2)
    return grp.sort_values("anio").reset_index(drop=True)


def clean_inflacion_ipc() -> pd.DataFrame:
    """Procesa la serie empalmada del IPC e Inflación mensual, acumulada y a 12 meses (1937-2026)."""
    path = RAW_DIR / "03_inflacion_ipc/ipc_nacional_variacion_acumulada_mensual.xlsx"
    xl = pd.ExcelFile(path)

    def parse_sheet(sheet_name: str, val_col: str) -> pd.DataFrame:
        df = pd.read_excel(xl, sheet_name=sheet_name, skiprows=4)
        valid_months = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        df = df[df['MES'].isin(valid_months)].copy()
        melted = df.melt(id_vars=['MES'], var_name='anio', value_name=val_col)
        melted['anio'] = pd.to_numeric(melted['anio'], errors='coerce')
        melted = melted.dropna(subset=['anio', val_col])
        melted['anio'] = melted['anio'].astype(int)
        melted[val_col] = pd.to_numeric(melted[val_col], errors='coerce').round(3)
        return melted

    df_acum = parse_sheet('CUADRO Nº 1.3 VAR ACUMULADA', 'inflacion_acumulada_pct')
    df_mens = parse_sheet('CUADRO Nº 1.2 VAR MENSUAL', 'inflacion_mensual_pct')
    df_12m = parse_sheet('CUADRO Nº 1.4 VAR 12 MESES', 'inflacion_12_meses_pct')
    df_ind = parse_sheet('CUADRO Nº 1.1 ÍNDICE MENSUAL', 'ipc_indice')

    merged = df_acum.merge(df_mens, on=['anio', 'MES'], how='outer')
    merged = merged.merge(df_12m, on=['anio', 'MES'], how='outer')
    merged = merged.merge(df_ind, on=['anio', 'MES'], how='outer')

    merged = merged.rename(columns={'MES': 'mes'})
    merged['mes_num'] = merged['mes'].str.lower().map(MESES_ES)
    merged = merged.sort_values(['anio', 'mes_num']).reset_index(drop=True)
    merged['periodo'] = merged['anio'].astype(str) + '-' + merged['mes_num'].astype(str).str.zfill(2)
    return merged


def clean_inflacion_anual() -> pd.DataFrame:
    """Procesa la serie histórica oficial de inflación anual acumulada al mes de diciembre (1937-2025)."""
    df = clean_inflacion_ipc()
    dic = df[df["mes"] == "Diciembre"].copy()
    dic = dic[["anio", "inflacion_acumulada_pct", "inflacion_12_meses_pct", "ipc_indice"]].dropna(subset=["inflacion_acumulada_pct"])
    dic = dic.rename(columns={
        "inflacion_acumulada_pct": "inflacion_anual_pct",
        "inflacion_12_meses_pct": "variacion_interanual_pct"
    })
    return dic.sort_values("anio").reset_index(drop=True)


def clean_pib_anual() -> pd.DataFrame:
    """Procesa la serie histórica del PIB anual a precios constantes por actividad económica (1980-2024)."""
    path = RAW_DIR / "01_pib_anual/pib_anual_precios_constantes_1980_2024.xlsx"
    df = pd.read_excel(path, sheet_name="06.01.01", skiprows=9)
    df = df.dropna(how="all")
    first_col = df.columns[1]
    df = df.rename(columns={first_col: "actividad_economica"})

    # Mapear columnas que representen años (incluyendo 2017(p), 2024(p))
    rename_cols = {}
    valid_cols = ["actividad_economica"]
    for c in df.columns:
        if c == "actividad_economica":
            continue
        parsed_y = parse_year_value(c)
        if parsed_y:
            rename_cols[c] = parsed_y
            valid_cols.append(c)

    df = df[valid_cols].rename(columns=rename_cols)
    df["actividad_economica"] = df["actividad_economica"].astype(str).str.strip()
    df = df[~df["actividad_economica"].str.lower().str.contains("fuente|nota|p/|preliminar|^nan$")]

    melted = df.melt(id_vars=["actividad_economica"], var_name="anio", value_name="pib_miles_bs_1990")
    melted["anio"] = pd.to_numeric(melted["anio"], errors="coerce").astype(int)
    melted["pib_miles_bs_1990"] = pd.to_numeric(melted["pib_miles_bs_1990"], errors="coerce").round(2)
    melted = melted.dropna(subset=["anio", "pib_miles_bs_1990"])
    melted = melted.sort_values(["anio", "actividad_economica"]).reset_index(drop=True)
    return melted


def clean_pib_trimestral() -> pd.DataFrame:
    """Procesa el PIB trimestral a precios constantes (1990-2024)."""
    path = RAW_DIR / "02_pib_trimestral/pib_trimestral_precios_constantes.xlsx"
    df = pd.read_excel(path, sheet_name="01.01.01", skiprows=9)
    df = df.dropna(how="all")
    period_col = df.columns[0]
    df = df.rename(columns={period_col: "periodo_raw"})

    records = []
    current_year = None
    activity_cols = [c for c in df.columns if c != "periodo_raw" and not str(c).startswith("Unnamed")]

    for _, row in df.iterrows():
        p_raw = str(row["periodo_raw"]).strip()
        parsed_y = parse_year_value(p_raw)
        if parsed_y and ("Trimestre" not in p_raw):
            current_year = parsed_y
            continue
        if "Trimestre" in p_raw and current_year:
            trimestre = p_raw.split()[0]
            for col in activity_cols:
                val = pd.to_numeric(row[col], errors="coerce")
                if pd.notna(val):
                    records.append({
                        "anio": current_year,
                        "trimestre": trimestre,
                        "periodo": f"{current_year}-T{trimestre}",
                        "actividad_economica": str(col).strip(),
                        "pib_miles_bs_1990": round(float(val), 2)
                    })

    res = pd.DataFrame(records)
    res = res.sort_values(["anio", "trimestre", "actividad_economica"]).reset_index(drop=True)
    return res


def clean_tasa_desocupacion() -> pd.DataFrame:
    """Procesa la tasa de desocupación urbana mensual desestacionalizada (2015-2026)."""
    path = RAW_DIR / "09_tasa_desocupacion/tasa_desocupacion_urbana_2015_2026.xlsx"
    df = pd.read_excel(path, sheet_name="3.05.01.13", header=None)

    years_row = df.iloc[4, 1:].ffill()
    months_row = df.iloc[5, 1:].astype(str).str.strip()
    total_row = df.iloc[7, 1:]
    men_row = df.iloc[8, 1:]
    women_row = df.iloc[9, 1:]

    res = []
    for c_idx in range(len(years_row)):
        y = years_row.iloc[c_idx]
        m = months_row.iloc[c_idx]
        tot = total_row.iloc[c_idx]
        h = men_row.iloc[c_idx]
        w = women_row.iloc[c_idx]
        if pd.notna(y) and pd.notna(m) and pd.notna(tot):
            try:
                anio_int = int(float(y))
                mes_str = str(m).strip()
                mes_num = MESES_ES.get(mes_str.lower(), 1)
                res.append({
                    "anio": anio_int,
                    "mes": mes_str,
                    "mes_num": mes_num,
                    "periodo": f"{anio_int}-{str(mes_num).zfill(2)}",
                    "tasa_desocupacion_total_pct": round(float(tot), 2),
                    "tasa_desocupacion_hombres_pct": round(float(h), 2) if pd.notna(h) else None,
                    "tasa_desocupacion_mujeres_pct": round(float(w), 2) if pd.notna(w) else None
                })
            except Exception:
                pass

    res_df = pd.DataFrame(res)
    res_df = res_df.sort_values(["anio", "mes_num"]).reset_index(drop=True)
    return res_df


def clean_pobreza_departamental() -> pd.DataFrame:
    """Procesa la población e incidencia de pobreza extrema por departamento (2011-2018)."""
    path = RAW_DIR / "08_pobreza_desigualdad/pobreza_incidencia_departamental_y_area.xlsx"
    df = pd.read_excel(path, sheet_name="3.06.01.07", header=None)

    years = [int(float(y)) for y in df.iloc[4, 1:] if pd.notna(y)]
    num_years = len(years)

    target_depts = [
        "BOLIVIA", "CHUQUISACA", "LA PAZ", "COCHABAMBA",
        "ORURO", "POTOSÍ", "TARIJA", "SANTA CRUZ", "BENI", "PANDO"
    ]

    records = []
    for r in range(5, len(df) - 3):
        val = str(df.iloc[r, 0]).strip()
        matched_dept = next((d for d in target_depts if d == val.upper() or val.upper().startswith(d)), None)
        if matched_dept and r + 3 < len(df):
            pop_tot = df.iloc[r + 1, 1:1 + num_years].values
            pop_pob = df.iloc[r + 2, 1:1 + num_years].values
            incid = df.iloc[r + 3, 1:1 + num_years].values

            for idx, y in enumerate(years):
                try:
                    records.append({
                        "anio": y,
                        "departamento": matched_dept,
                        "poblacion_total": int(float(pop_tot[idx])),
                        "poblacion_pobreza_extrema": int(float(pop_pob[idx])),
                        "incidencia_pobreza_extrema_pct": round(float(incid[idx]), 2)
                    })
                except Exception:
                    pass

    res = pd.DataFrame(records)
    res = res.sort_values(["anio", "departamento"]).reset_index(drop=True)
    return res


def clean_igae() -> pd.DataFrame:
    """Procesa el Índice Global de Actividad Económica (IGAE) mensual (2008-2024)."""
    path = RAW_DIR / "10_igae/igae_mensual_y_acumulado_2008_2024.xlsx"
    df = pd.read_excel(path, sheet_name="01.02", header=None)

    # Convertir encabezados de años limpiando '(p)' y forward-fill
    years_raw = [parse_year_value(x) for x in df.iloc[9, 1:]]
    years_series = pd.Series(years_raw).ffill()
    months_row = df.iloc[10, 1:]
    igae_row = df.iloc[11, 1:]

    records = []
    for idx in range(len(years_series)):
        y = years_series.iloc[idx]
        m = months_row.iloc[idx]
        val = igae_row.iloc[idx]
        if pd.notna(y) and pd.notna(m) and pd.notna(val):
            try:
                anio_int = int(float(y))
                mes_str = str(m).strip()
                mes_num = MESES_ES.get(mes_str.lower(), 1)
                records.append({
                    "anio": anio_int,
                    "mes": mes_str,
                    "mes_num": mes_num,
                    "periodo": f"{anio_int}-{str(mes_num).zfill(2)}",
                    "igae_indice": round(float(val), 2)
                })
            except Exception:
                pass

    res = pd.DataFrame(records)
    res = res.sort_values(["anio", "mes_num"]).reset_index(drop=True)
    return res


def clean_exportaciones() -> pd.DataFrame:
    """Procesa las exportaciones anuales según actividad económica y producto (1992-2026)."""
    path = RAW_DIR / "05_exportaciones/exportaciones_actividad_y_producto_1992_2026.xlsx"
    df = pd.read_excel(path, sheet_name="ExpActProdAño 92-26 Valor", skiprows=4)

    product_col = "ACTIVIDAD ECONÓMICA Y PRODUCTO"
    year_cols = [c for c in df.columns if str(c).strip().isdigit()]

    df = df[[product_col] + year_cols].dropna(subset=[product_col])
    df[product_col] = df[product_col].astype(str).str.strip()
    df = df[~df[product_col].str.lower().str.contains("fuente|nota|p/|preliminar|^nan$")]

    melted = df.melt(id_vars=[product_col], var_name="anio", value_name="valor_fob_usd_millones")
    melted = melted.rename(columns={product_col: "actividad_o_producto"})
    melted["anio"] = pd.to_numeric(melted["anio"], errors="coerce").astype(int)
    melted["valor_fob_usd_millones"] = pd.to_numeric(melted["valor_fob_usd_millones"], errors="coerce").round(2)
    melted = melted.dropna(subset=["anio", "valor_fob_usd_millones"])
    melted = melted.sort_values(["anio", "actividad_o_producto"]).reset_index(drop=True)
    return melted


def clean_importaciones() -> pd.DataFrame:
    """Procesa las importaciones mensuales por año y mes (1992-2026)."""
    path = RAW_DIR / "06_importaciones/importaciones_por_ano_y_mes_1992_2026.xlsx"
    df = pd.read_excel(path, sheet_name="Importaciones_1992_2026", skiprows=3)

    df["GESTIIÓN"] = pd.to_numeric(df["GESTIIÓN"], errors="coerce").ffill()
    df = df.dropna(subset=["GESTIIÓN", "MES", "VALOR CIF"])
    df["MES"] = df["MES"].astype(str).str.strip()
    valid_months = list(MESES_ES.keys())
    df = df[df["MES"].str.lower().isin(valid_months)].copy()

    df = df.rename(columns={
        "GESTIIÓN": "anio",
        "MES": "mes",
        "PESO BRUTO": "peso_bruto_kg",
        "VALOR FOB": "valor_fob_usd",
        "VALOR CIF": "valor_cif_usd"
    })
    df["anio"] = df["anio"].astype(int)
    df["mes_num"] = df["mes"].str.lower().map(MESES_ES)
    df["periodo"] = df["anio"].astype(str) + "-" + df["mes_num"].astype(str).str.zfill(2)
    df["valor_cif_usd_millones"] = (df["valor_cif_usd"] / 1e6).round(2)

    df = df.sort_values(["anio", "mes_num"]).reset_index(drop=True)
    return df


def clean_lineas_pobreza() -> pd.DataFrame:
    """Procesa las líneas monetarias de pobreza y pobreza extrema en Bs por persona/mes (1989-2018)."""
    path = RAW_DIR / "11_lineas_pobreza/lineas_de_pobreza_monetaria_bs.xlsx"
    df = pd.read_excel(path, sheet_name="3.06.01.05", skiprows=3)

    area_col = df.columns[0]
    year_cols = [c for c in df.columns if c != area_col and not str(c).startswith("Unnamed")]

    records = []
    for _, row in df.iterrows():
        area = str(row[area_col]).strip()
        if not area or any(k in area.lower() for k in ["fuente", "nota", "cuadro", "bolivia:"]):
            continue
        for col in year_cols:
            val = pd.to_numeric(row[col], errors="coerce")
            if pd.notna(val):
                # Extraer año
                period_str = str(col).strip()
                anio_match = "".join(filter(str.isdigit, period_str))
                anio = int(anio_match[-4:]) if len(anio_match) >= 4 else None
                if anio:
                    records.append({
                        "anio": anio,
                        "periodo": period_str,
                        "area_o_ciudad": area,
                        "linea_pobreza_bs_mes": round(float(val), 2)
                    })

    res = pd.DataFrame(records)
    res = res.sort_values(["anio", "area_o_ciudad"]).reset_index(drop=True)
    return res


def clean_salario_medio() -> pd.DataFrame:
    """Procesa el salario medio nominal por grupo ocupacional del sector privado (1996-2023)."""
    path = RAW_DIR / "12_salario_medio_nominal/salario_medio_nominal_sector_privado.xlsx"
    df = pd.read_excel(path, sheet_name="INDICE-NOMINAL-OCUPACION", skiprows=7)

    period_col = df.columns[0]
    df = df.dropna(subset=[period_col])
    occupations = [c for c in df.columns if c != period_col and not str(c).startswith("Unnamed")]

    records = []
    current_year = None
    for _, row in df.iterrows():
        p_val = str(row[period_col]).strip()
        if p_val.isdigit() and len(p_val) == 4:
            current_year = int(p_val)
            for occ in occupations:
                v = pd.to_numeric(row[occ], errors="coerce")
                if pd.notna(v):
                    records.append({
                        "anio": current_year,
                        "grupo_ocupacional": str(occ).strip(),
                        "indice_salario_nominal": round(float(v), 2)
                    })

    res = pd.DataFrame(records)
    res = res.sort_values(["anio", "grupo_ocupacional"]).reset_index(drop=True)
    return res


def load_all_clean_datasets() -> Dict[str, pd.DataFrame]:
    """Carga y limpia todos los datasets disponibles en un diccionario unificado."""
    return {
        # Sección 1: Cuentas Nacionales & Actividad Económica (Anual -> Trimestral -> Mensual)
        "pib_anual": clean_pib_anual(),
        "pib_trimestral": clean_pib_trimestral(),
        "igae": clean_igae(),

        # Sección 2: Sector Externo & Comercio (Anual -> Mensual)
        "balanza_comercial_anual": clean_balanza_comercial_anual(),
        "exportaciones": clean_exportaciones(),
        "balanza_comercial": clean_balanza_comercial(),
        "importaciones": clean_importaciones(),

        # Sección 3: Precios e Inflación (Anual -> Mensual)
        "inflacion_anual": clean_inflacion_anual(),
        "inflacion_ipc": clean_inflacion_ipc(),

        # Sección 4: Pobreza, Empleo y Condiciones Sociales (Anual -> Mensual)
        "pobreza_departamental": clean_pobreza_departamental(),
        "lineas_pobreza": clean_lineas_pobreza(),
        "salario_medio_nominal": clean_salario_medio(),
        "tasa_desocupacion": clean_tasa_desocupacion()
    }
