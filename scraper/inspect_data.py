"""
Herramienta de inspección y validación de los Excels descargados del INE.
Permite ver las primeras filas de datos de cada indicador para demostrar
la integridad y facilidad de procesamiento para la futura web de matrices.
"""

import json
from pathlib import Path
import pandas as pd

from scraper.config import RAW_DATA_DIR, METADATA_DIR

def inspect_all():
    catalog_path = METADATA_DIR / "catalog.json"
    if not catalog_path.exists():
        print("El catálogo no existe. Ejecuta run_pipeline.py primero.")
        return

    with open(catalog_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    print("\n" + "=" * 90)
    print(" INSPECCIÓN DE ESTRUCTURA DE DATOS DE LOS EXCELS OFICIALES DEL INE")
    print("=" * 90)

    for ind in catalog["indicators"]:
        if ind.get("status") != "SUCCESS":
            continue

        file_path = RAW_DATA_DIR / ind["id"] / ind["canonical_filename"]
        print(f"\n📁 [{ind['id']}] {ind['name']}")
        print(f"   Archivo: {file_path.name} | Tamaño: {ind['file_size_kb']} KB")
        print(f"   Fuente INE: {ind['source_page']}")

        try:
            # Leer nombres de hojas
            xl = pd.ExcelFile(file_path)
            sheets = xl.sheet_names
            print(f"   Hojas disponibles ({len(sheets)}): {', '.join(sheets[:5])}")

            # Tomar la hoja de datos principal (evitando carátulas 'INICIO' si hay varias)
            target_sheet = sheets[1] if len(sheets) > 1 and sheets[0].upper() in ["INICIO", "INDICE", "PORTADA"] else sheets[0]
            df = pd.read_excel(file_path, sheet_name=target_sheet, header=None, nrows=12)

            print(f"   Vista previa de hoja: '{target_sheet}' (primeras 6 filas no vacías):")
            # Mostrar filas con contenido relevante
            non_empty_rows = 0
            for idx, row in df.iterrows():
                vals = [str(v).strip() for v in row.values if pd.notna(v) and str(v).strip() != ""]
                if vals:
                    print(f"     Fila {idx + 1:2d}: {' | '.join(vals[:6])}")
                    non_empty_rows += 1
                    if non_empty_rows >= 6:
                        break

        except Exception as e:
            print(f"   Error al inspeccionar hoja: {e}")

if __name__ == "__main__":
    inspect_all()
