"""
Módulo de descarga y extracción de los archivos Excel del INE Bolivia.
Realiza scraping dinámico en las páginas oficiales y descarga los datasets con control de errores.
"""

import os
import re
import json
import logging
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

import requests
import urllib3
from bs4 import BeautifulSoup
import openpyxl

from scraper.config import INDICATORS, HEADERS, RAW_DATA_DIR, METADATA_DIR

# Silenciar advertencias de certificados auto-firmados en servidores estatales
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("ine_scraper")


class INEScraper:
    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update(HEADERS)
        self.session.verify = False

        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        METADATA_DIR.mkdir(parents=True, exist_ok=True)

    def find_download_link(self, source_page: str, pattern: str) -> Optional[str]:
        """
        Scrapea la página oficial del INE buscando enlaces a nube.ine.gob.bo o nimbus
        que coincidan con el patrón del cuadro estadístico.
        """
        try:
            r = self.session.get(source_page, timeout=15)
            if r.status_code != 200:
                logger.warning(f"Error HTTP {r.status_code} al acceder a {source_page}")
                return None

            soup = BeautifulSoup(r.text, "html.parser")
            regex = re.compile(pattern, re.IGNORECASE)

            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                text = a.get_text(strip=True)

                # Verificar si es un enlace de descarga en la nube oficial del INE
                if ("nube.ine.gob.bo" in href or "nimbus.ine.gob.bo" in href or "download" in href):
                    if regex.search(text) or regex.search(href):
                        # Asegurar enlace con /download si es un share link
                        if "/s/" in href and not href.endswith("/download"):
                            href = href.rstrip("/") + "/download"
                        return href

            logger.info(f"Patrón '{pattern}' no encontrado en HTML, se usará enlace directo preconfigurado.")
            return None
        except Exception as e:
            logger.warning(f"Excepción al scrapear {source_page}: {e}")
            return None

    def extract_filename_from_cd(self, content_disposition: str) -> Optional[str]:
        """Extrae el nombre de archivo del encabezado Content-Disposition."""
        if not content_disposition:
            return None

        # Patrón RFC 5987: filename*=UTF-8''...
        match_utf8 = re.search(r"filename\*=UTF-8''([^;]+)", content_disposition, re.IGNORECASE)
        if match_utf8:
            return urllib.parse.unquote(match_utf8.group(1).strip('"\''))

        # Patrón clásico: filename="..."
        match_std = re.search(r'filename="?([^";]+)"?', content_disposition, re.IGNORECASE)
        if match_std:
            name = match_std.group(1).strip('"\'')
            return urllib.parse.unquote(name)

        return None

    def inspect_excel_file(self, file_path: Path) -> Dict[str, Any]:
        """Inspecciona metadatos y estructura interna de un archivo Excel."""
        try:
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            sheets = wb.sheetnames
            details = {"sheet_count": len(sheets), "sheets": []}

            for name in sheets[:6]:
                try:
                    sheet = wb[name]
                    max_row = sheet.max_row or 0
                    max_col = sheet.max_column or 0
                    details["sheets"].append({
                        "name": name,
                        "rows": max_row,
                        "columns": max_col
                    })
                except Exception:
                    details["sheets"].append({"name": name, "rows": 0, "columns": 0})

            wb.close()
            return details
        except Exception as e:
            logger.warning(f"No se pudo leer la estructura interna de {file_path.name}: {e}")
            return {"sheet_count": 0, "sheets": [], "error": str(e)}

    def download_indicator(self, ind: Dict[str, Any]) -> Dict[str, Any]:
        """
        Descarga y organiza un indicador específico.
        """
        ind_id = ind["id"]
        logger.info(f"Iniciando descarga de: {ind['name']} ({ind_id})")

        # 1. Intentar descubrir el enlace dinámicamente o usar el directo
        scraped_url = self.find_download_link(ind["source_page"], ind["link_pattern"])
        download_url = scraped_url or ind["direct_url"]

        # 2. Carpeta de destino
        dest_folder = RAW_DATA_DIR / ind_id
        dest_folder.mkdir(parents=True, exist_ok=True)

        canonical_path = dest_folder / ind["canonical_filename"]

        # 3. Descargar archivo
        try:
            r = self.session.get(download_url, stream=True, timeout=30)
            r.raise_for_status()

            cd = r.headers.get("Content-Disposition", "")
            original_filename = self.extract_filename_from_cd(cd) or ind["canonical_filename"]

            # Guardar con nombre canónico limpio
            with open(canonical_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)

            file_size_bytes = canonical_path.stat().st_size
            file_size_kb = round(file_size_bytes / 1024, 2)

            # 4. Inspeccionar archivo Excel
            excel_info = self.inspect_excel_file(canonical_path)

            record = {
                "id": ind_id,
                "name": ind["name"],
                "category": ind["category"],
                "frequency": ind["frequency"],
                "description": ind["description"],
                "source_page": ind["source_page"],
                "download_url": download_url,
                "dynamic_scraped": bool(scraped_url),
                "original_filename": original_filename,
                "canonical_filename": ind["canonical_filename"],
                "local_path": str(canonical_path.relative_to(RAW_DATA_DIR.parent.parent)),
                "file_size_bytes": file_size_bytes,
                "file_size_kb": file_size_kb,
                "downloaded_at": datetime.now().isoformat(),
                "excel_info": excel_info,
                "status": "SUCCESS"
            }
            logger.info(f"✓ Éxito: {ind['canonical_filename']} ({file_size_kb} KB, {excel_info['sheet_count']} hojas)")
            return record

        except Exception as e:
            logger.error(f"✗ Falló la descarga de {ind_id}: {e}")
            return {
                "id": ind_id,
                "name": ind["name"],
                "status": "FAILED",
                "error": str(e),
                "download_url": download_url
            }

    def run_all(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Descarga todos los indicadores y genera el catálogo de metadatos."""
        indicators_to_process = INDICATORS[:limit] if limit else INDICATORS
        results = []

        for ind in indicators_to_process:
            res = self.download_indicator(ind)
            results.append(res)

        self.save_metadata(results)
        return results

    def save_metadata(self, results: List[Dict[str, Any]]):
        """Genera archivos JSON y Markdown con el catálogo consolidado."""
        json_path = METADATA_DIR / "catalog.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({
                "source": "Instituto Nacional de Estadística (INE) - Bolivia",
                "portal_url": "https://www.ine.gob.bo/",
                "generated_at": datetime.now().isoformat(),
                "indicators_count": len(results),
                "successful_downloads": sum(1 for r in results if r.get("status") == "SUCCESS"),
                "indicators": results
            }, f, indent=2, ensure_ascii=False)

        md_path = METADATA_DIR / "catalog.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# Catálogo Oficial de Indicadores Económicos y Sociales - INE Bolivia\n\n")
            f.write(f"**Fecha de generación:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Fuente oficial:** [Instituto Nacional de Estadística (INE)](https://www.ine.gob.bo/)\n\n")
            f.write("| ID | Indicador | Categoría | Frecuencia | Tamaño | Hojas Excel | Archivo Local |\n")
            f.write("|---|---|---|---|---|---|---|\n")

            for r in results:
                if r.get("status") == "SUCCESS":
                    sheets_cnt = r["excel_info"]["sheet_count"]
                    f.write(
                        f"| `{r['id']}` | **{r['name']}** | {r['category']} | {r['frequency']} | "
                        f"{r['file_size_kb']} KB | {sheets_cnt} | [`{r['canonical_filename']}`](../raw/{r['id']}/{r['canonical_filename']}) |\n"
                    )

            f.write("\n## Detalle de Hojas y Contenido por Indicador\n\n")
            for r in results:
                if r.get("status") == "SUCCESS":
                    f.write(f"### {r['id']} - {r['name']}\n")
                    f.write(f"- **Descripción:** {r['description']}\n")
                    f.write(f"- **Página INE:** [{r['source_page']}]({r['source_page']})\n")
                    f.write(f"- **URL Descarga:** [{r['download_url']}]({r['download_url']})\n")
                    f.write(f"- **Nombre original servidor:** `{r['original_filename']}`\n")
                    f.write(f"- **Hojas encontradas:**\n")
                    for s in r["excel_info"]["sheets"]:
                        f.write(f"  - `{s['name']}` ({s['rows']} filas x {s['columns']} columnas)\n")
                    f.write("\n")

        logger.info(f"Metadatos guardados en {json_path} y {md_path}")
