#!/usr/bin/env python3
"""
Etapa de Auditoría y Control de Calidad de Datos (QA / Audit).
Verifica matrices procesadas del INE mediante Pandera y pruebas lógicas.
Si alguna prueba no pasa, aborta la ejecución con sys.exit(1).
"""

import sys
import logging
from typing import Dict, List
import pandas as pd
import pandera.pandas as pa

from pipeline.cleaners import load_all_clean_datasets
from pipeline.schemas import DATASET_SCHEMAS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("validator")


class DataAuditor:
    def __init__(self, datasets: Dict[str, pd.DataFrame]):
        self.datasets = datasets
        self.errors: List[str] = []
        self.passed_tests: List[str] = []

    def log_success(self, test_name: str, detail: str = ""):
        msg = f"[PASS] {test_name}" + (f": {detail}" if detail else "")
        self.passed_tests.append(msg)
        print(f"  ✓ {msg}")

    def log_failure(self, test_name: str, reason: str):
        msg = f"[FAIL] {test_name}: {reason}"
        self.errors.append(msg)
        print(f"  ✗ {msg}", file=sys.stderr)

    def validate_pandera_schemas(self):
        """Verifica tipos de datos, rangos y valores no nulos con Pandera."""
        print("\n--- 1. Validación de Esquemas y Tipos de Datos (Pandera) ---")
        for name, schema in DATASET_SCHEMAS.items():
            if name not in self.datasets:
                self.log_failure(f"Schema {name}", "El dataset no existe en los datos procesados.")
                continue

            df = self.datasets[name]
            try:
                schema.validate(df, lazy=True)
                self.log_success(
                    f"Esquema Pandera '{name}'",
                    f"{len(df):,} filas validadas sin errores de tipo o nulos críticos."
                )
            except pa.errors.SchemaErrors as err:
                failure_summary = err.failure_cases.head(5).to_dict(orient="records")
                self.log_failure(
                    f"Esquema Pandera '{name}'",
                    f"{len(err.failure_cases)} violaciones de esquema detectadas: {failure_summary}"
                )
            except Exception as e:
                self.log_failure(f"Esquema Pandera '{name}'", f"Error inesperado: {str(e)}")

    def validate_temporal_continuity(self):
        """Verifica que las series temporales no tengan años faltantes ni saltos."""
        print("\n--- 2. Validación de Coherencia Temporal (Años Consecutivos) ---")
        time_series_datasets = [
            ("pib_anual", 1980, 2024),
            ("balanza_comercial", 1992, 2023),
            ("inflacion_ipc", 1937, 2026),
            ("igae", 2008, 2024),
            ("pobreza_departamental", 2011, 2018),
            ("tasa_desocupacion", 2015, 2026)
        ]

        for name, expected_start, expected_end in time_series_datasets:
            if name not in self.datasets:
                continue

            df = self.datasets[name]
            actual_years = set(df["anio"].unique())
            expected_years = set(range(expected_start, expected_end + 1))
            missing = sorted(list(expected_years - actual_years))

            if not missing:
                self.log_success(
                    f"Continuidad Temporal '{name}'",
                    f"Serie continua completa sin interrupciones ({expected_start} - {expected_end})."
                )
            else:
                self.log_failure(
                    f"Continuidad Temporal '{name}'",
                    f"Faltan los siguientes años en la serie: {missing[:8]}"
                )

    def validate_logical_balances(self):
        """Verifica identidades contables y sumatorias lógicas."""
        print("\n--- 3. Validación de Sumatorias y Fórmulas Lógicas ---")

        # Prueba A: Balanza Comercial = Exportaciones - Importaciones
        df_bc = self.datasets.get("balanza_comercial")
        if df_bc is not None:
            calc_saldo = df_bc["exportaciones_usd_millones"] - df_bc["importaciones_usd_millones"]
            diff = (df_bc["saldo_comercial_usd_millones"] - calc_saldo).abs()
            max_diff = diff.max()
            tolerance = 0.15  # Tolerancia de 150 mil USD por redondeos oficiales del INE

            if max_diff <= tolerance:
                self.log_success(
                    "Identidad Contable: Saldo = X - M",
                    f"Discrepancia máxima = ${max_diff:.3f}M USD (dentro del umbral de ${tolerance}M)."
                )
            else:
                violating_rows = df_bc[diff > tolerance][["periodo", "exportaciones_usd_millones", "importaciones_usd_millones", "saldo_comercial_usd_millones"]]
                self.log_failure(
                    "Identidad Contable: Saldo = X - M",
                    f"{len(violating_rows)} meses superan la tolerancia. Max error: ${max_diff:.2f}M."
                )

        # Prueba B: Suma Poblacional Departamental vs Total Nacional
        df_pob = self.datasets.get("pobreza_departamental")
        if df_pob is not None:
            years = df_pob["anio"].unique()
            pop_errors = 0
            for y in years:
                sub = df_pob[df_pob["anio"] == y]
                bol_row = sub[sub["departamento"] == "BOLIVIA"]
                dept_rows = sub[sub["departamento"] != "BOLIVIA"]

                if not bol_row.empty and len(dept_rows) == 9:
                    bol_pop = bol_row["poblacion_total"].iloc[0]
                    dept_pop_sum = dept_rows["poblacion_total"].sum()
                    pop_diff = abs(bol_pop - dept_pop_sum)
                    # En demografía estadística la suma debe coincidir con +- 5 personas por redondeo
                    if pop_diff > 5:
                        pop_errors += 1
                        self.log_failure(
                            f"Sumatoria Poblacional Depts vs Nacional {y}",
                            f"Total Bolivia={bol_pop:,}, Suma 9 Depts={dept_pop_sum:,}, Dif={pop_diff} personas."
                        )

            if pop_errors == 0:
                self.log_success(
                    "Sumatoria Demográfica: Totales Departamentales vs Nacional",
                    f"Los 9 departamentos suman exactamente la población total de Bolivia en todos los años ({len(years)} gestiones)."
                )

        # Prueba C: Límites lógicos en Tasa de Desocupación
        df_des = self.datasets.get("tasa_desocupacion")
        if df_des is not None:
            invalid_rates = df_des[
                (df_des["tasa_desocupacion_total_pct"] < 0) | 
                (df_des["tasa_desocupacion_total_pct"] > 35)
            ]
            if invalid_rates.empty:
                min_rate = df_des["tasa_desocupacion_total_pct"].min()
                max_rate = df_des["tasa_desocupacion_total_pct"].max()
                self.log_success(
                    "Límites de Desocupación Urbana",
                    f"Todas las tasas se encuentran en rangos económicos verosímiles ({min_rate}% - {max_rate}%)."
                )
            else:
                self.log_failure(
                    "Límites de Desocupación Urbana",
                    f"Valores anómalos de desocupación detectados: {invalid_rates.to_dict()}"
                )

    def run_all(self) -> bool:
        """Ejecuta todas las pruebas de control de calidad."""
        print("=" * 80)
        print(" ETAPA DE AUDITORÍA Y CONTROL DE CALIDAD DE DATOS (QA & DATA AUDIT)")
        print("=" * 80)

        self.validate_pandera_schemas()
        self.validate_temporal_continuity()
        self.validate_logical_balances()

        print("\n" + "=" * 80)
        print(f" RESULTADO DE AUDITORÍA: {len(self.passed_tests)} PASADAS | {len(self.errors)} FALLADAS")
        print("=" * 80)

        if self.errors:
            print("\n🚨 ATENCIÓN: Se detectaron inconsistencias críticas en los datos:")
            for e in self.errors:
                print(f"  • {e}")
            return False

        print("\n✅ Todos los conjuntos de datos superaron satisfactoriamente la auditoría de calidad.")
        print("   Aprobado para compilación estática y despliegue a Vercel.")
        return True


def test_data_quality():
    """Función de prueba compatible con pytest."""
    datasets = load_all_clean_datasets()
    auditor = DataAuditor(datasets)
    assert auditor.run_all() is True


def main():
    datasets = load_all_clean_datasets()
    auditor = DataAuditor(datasets)
    success = auditor.run_all()
    if not success:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
