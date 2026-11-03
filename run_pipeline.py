#!/usr/bin/env python3
"""
Script principal para ejecutar la descarga, validación y organización
de los Excels del Instituto Nacional de Estadística (INE) de Bolivia.
"""

import sys
from scraper.ine_scraper import INEScraper

def main():
    print("=" * 80)
    print(" PIPELINE DE EXTRACCIÓN Y ORGANIZACIÓN DE DATOS INE BOLIVIA")
    print(" Portal Oficial: https://www.ine.gob.bo/")
    print("=" * 80)

    scraper = INEScraper()
    results = scraper.run_all()

    successes = [r for r in results if r.get("status") == "SUCCESS"]
    failures = [r for r in results if r.get("status") != "SUCCESS"]

    print("\n" + "=" * 80)
    print(f" RESUMEN DE EJECUCIÓN: {len(successes)}/{len(results)} indicadores descargados correctamente")
    print("=" * 80)

    for r in successes:
        print(f"  ✓ [{r['id']}] {r['name']}")
        print(f"     Archivo: {r['canonical_filename']} ({r['file_size_kb']} KB)")
        print(f"     Hojas:   {', '.join([s['name'] for s in r['excel_info']['sheets'][:3]])}...")
        print()

    if failures:
        print("\nErrores:")
        for f in failures:
            print(f"  ✗ [{f['id']}] {f['name']}: {f.get('error')}")

    print("=" * 80)
    print(f"Archivos guardados en: ./data/raw/")
    print(f"Catálogo generado en:  ./data/metadata/catalog.json y ./data/metadata/catalog.md")
    print("=" * 80)

if __name__ == "__main__":
    main()
