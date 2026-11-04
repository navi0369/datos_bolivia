"""
Esquemas de validación de calidad de datos usando Pandera.
Garantiza tipos de datos, no nulidad de columnas críticas y rangos lógicos permitidos.
"""

import pandera.pandas as pa
from pandera.pandas import Column, Check, DataFrameSchema

# Check macroeconómico: el PIB es positivo para actividades productivas, 
# permitiendo valores negativos únicamente para ajustes contables oficiales (Servicios Bancarios Imputados).
def check_pib_values(df):
    invalid = df[(df["actividad_economica"] != "SERVICIOS BANCARIOS IMPUTADOS") & (df["pib_miles_bs_1990"] < 0)]
    return invalid.empty

# 1. Esquema Balanza Comercial Mensual y Anual
SCHEMA_BALANZA_COMERCIAL = DataFrameSchema(
    columns={
        "anio": Column(int, Check.between(1990, 2035), nullable=False),
        "mes": Column(str, nullable=False),
        "mes_num": Column(int, Check.between(1, 12), nullable=False),
        "periodo": Column(str, Check.str_matches(r"^\d{4}-\d{2}$"), nullable=False),
        "exportaciones_usd_millones": Column(float, Check.greater_than_or_equal_to(0.0), nullable=False),
        "importaciones_usd_millones": Column(float, Check.greater_than_or_equal_to(0.0), nullable=False),
        "saldo_comercial_usd_millones": Column(float, nullable=False),
    },
    strict=False,
    coerce=True
)

SCHEMA_BALANZA_COMERCIAL_ANUAL = DataFrameSchema(
    columns={
        "anio": Column(int, Check.between(1990, 2035), nullable=False),
        "exportaciones_usd_millones": Column(float, Check.greater_than_or_equal_to(0.0), nullable=False),
        "importaciones_usd_millones": Column(float, Check.greater_than_or_equal_to(0.0), nullable=False),
        "saldo_comercial_usd_millones": Column(float, nullable=False),
    },
    strict=False,
    coerce=True
)

SCHEMA_INFLACION_ANUAL = DataFrameSchema(
    columns={
        "anio": Column(int, Check.between(1930, 2035), nullable=False),
        "inflacion_anual_pct": Column(float, nullable=False),
        "variacion_interanual_pct": Column(float, nullable=False),
        "ipc_indice": Column(float, Check.greater_than_or_equal_to(0.0), nullable=False),
    },
    strict=False,
    coerce=True
)

# 2. Esquema Inflación e IPC
SCHEMA_INFLACION_IPC = DataFrameSchema(
    columns={
        "anio": Column(int, Check.between(1930, 2035), nullable=False),
        "mes": Column(str, nullable=False),
        "mes_num": Column(int, Check.between(1, 12), nullable=False),
        "periodo": Column(str, Check.str_matches(r"^\d{4}-\d{2}$"), nullable=False),
        "inflacion_acumulada_pct": Column(float, nullable=True),
        "inflacion_mensual_pct": Column(float, nullable=True),
        "inflacion_12_meses_pct": Column(float, nullable=True),
        "ipc_indice": Column(float, Check.greater_than_or_equal_to(0.0), nullable=True),
    },
    strict=False,
    coerce=True
)

# 3. Esquema PIB Anual
SCHEMA_PIB_ANUAL = DataFrameSchema(
    columns={
        "anio": Column(int, Check.between(1970, 2035), nullable=False),
        "actividad_economica": Column(str, nullable=False),
        "pib_miles_bs_1990": Column(float, nullable=False),
    },
    checks=[
        Check(check_pib_values, error="Existen sectores productivos del PIB anual con valores negativos ilegítimos")
    ],
    strict=False,
    coerce=True
)

# 4. Esquema PIB Trimestral
SCHEMA_PIB_TRIMESTRAL = DataFrameSchema(
    columns={
        "anio": Column(int, Check.between(1980, 2035), nullable=False),
        "trimestre": Column(str, Check.isin(["I", "II", "III", "IV"]), nullable=False),
        "periodo": Column(str, nullable=False),
        "actividad_economica": Column(str, nullable=False),
        "pib_miles_bs_1990": Column(float, nullable=False),
    },
    checks=[
        Check(check_pib_values, error="Existen sectores productivos del PIB trimestral con valores negativos ilegítimos")
    ],
    strict=False,
    coerce=True
)

# 5. Esquema Tasa de Desocupación
SCHEMA_TASA_DESOCUPACION = DataFrameSchema(
    columns={
        "anio": Column(int, Check.between(2010, 2035), nullable=False),
        "mes": Column(str, nullable=False),
        "mes_num": Column(int, Check.between(1, 12), nullable=False),
        "periodo": Column(str, nullable=False),
        "tasa_desocupacion_total_pct": Column(float, Check.between(0.0, 50.0), nullable=False),
        "tasa_desocupacion_hombres_pct": Column(float, Check.between(0.0, 50.0), nullable=True),
        "tasa_desocupacion_mujeres_pct": Column(float, Check.between(0.0, 50.0), nullable=True),
    },
    strict=False,
    coerce=True
)

# 6. Esquema Pobreza Departamental
SCHEMA_POBREZA_DEPARTAMENTAL = DataFrameSchema(
    columns={
        "anio": Column(int, Check.between(2000, 2035), nullable=False),
        "departamento": Column(str, nullable=False),
        "poblacion_total": Column(int, Check.greater_than(0), nullable=False),
        "poblacion_pobreza_extrema": Column(int, Check.greater_than_or_equal_to(0), nullable=False),
        "incidencia_pobreza_extrema_pct": Column(float, Check.between(0.0, 100.0), nullable=False),
    },
    strict=False,
    coerce=True
)

# 7. Esquema IGAE
SCHEMA_IGAE = DataFrameSchema(
    columns={
        "anio": Column(int, Check.between(2000, 2035), nullable=False),
        "mes": Column(str, nullable=False),
        "mes_num": Column(int, Check.between(1, 12), nullable=False),
        "periodo": Column(str, nullable=False),
        "igae_indice": Column(float, Check.greater_than(0.0), nullable=False),
    },
    strict=False,
    coerce=True
)

# Diccionario de esquemas mapeados por nombre de dataset
DATASET_SCHEMAS = {
    "balanza_comercial": SCHEMA_BALANZA_COMERCIAL,
    "balanza_comercial_anual": SCHEMA_BALANZA_COMERCIAL_ANUAL,
    "inflacion_anual": SCHEMA_INFLACION_ANUAL,
    "inflacion_ipc": SCHEMA_INFLACION_IPC,
    "pib_anual": SCHEMA_PIB_ANUAL,
    "pib_trimestral": SCHEMA_PIB_TRIMESTRAL,
    "tasa_desocupacion": SCHEMA_TASA_DESOCUPACION,
    "pobreza_departamental": SCHEMA_POBREZA_DEPARTAMENTAL,
    "igae": SCHEMA_IGAE,
}
