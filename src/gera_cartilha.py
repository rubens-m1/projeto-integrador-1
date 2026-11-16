"""
Exporta a cartilha "Golpe da maquininha" (src/cartilha/cartilha_golpe_maquininha.html, página A4)
para PNG (Figura 13 do relatório) e PDF (distribuição), usando o Edge ou o Chrome em modo headless.

Uso:  python -I src/gera_cartilha.py   (a partir da pasta proj-integrador-1)
Saídas: figures/fig13_cartilha_golpe_maquininha.png e relatorio/Cartilha_Golpe_da_Maquininha.pdf
As fontes (Archivo e Inter) vêm do Google Fonts: sem internet, o navegador usa Arial.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "src" / "cartilha" / "cartilha_golpe_maquininha.html"
PNG = ROOT / "figures" / "fig13_cartilha_golpe_maquininha.png"
PDF = ROOT / "relatorio" / "Cartilha_Golpe_da_Maquininha.pdf"

CANDIDATOS = [
    Path(os.environ.get("ProgramFiles(x86)", "")) / "Microsoft/Edge/Application/msedge.exe",
    Path(os.environ.get("ProgramFiles", "")) / "Microsoft/Edge/Application/msedge.exe",
    Path(os.environ.get("ProgramFiles", "")) / "Google/Chrome/Application/chrome.exe",
]
nav = next((p for p in CANDIDATOS if p.is_file()), None) or shutil.which("msedge") or shutil.which("chrome")
if not nav:
    raise SystemExit("Edge ou Chrome não encontrado.")

url = HTML.as_uri()
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as perfil:
    base = [str(nav), "--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars",
            f"--user-data-dir={perfil}", "--virtual-time-budget=8000",
            "--run-all-compositor-stages-before-draw"]
    inicio = time.time()
    subprocess.run(base + ["--no-pdf-header-footer", f"--print-to-pdf={PDF}", url], check=True, timeout=120)

# O Edge pode terminar de gravar o PDF depois que o processo retorna: espera o arquivo novo estabilizar.
tam_ant = -1
for _ in range(60):
    if PDF.exists() and PDF.stat().st_mtime >= inicio - 1 and PDF.stat().st_size == tam_ant:
        break
    tam_ant = PDF.stat().st_size if PDF.exists() else -1
    time.sleep(0.5)
else:
    raise SystemExit("O PDF da cartilha não foi gravado.")

# A figura do relatório é o próprio PDF rasterizado (idêntica ao que se distribui).
import pypdfium2 as pdfium  # noqa: E402

pdf = pdfium.PdfDocument(str(PDF))
if len(pdf) != 1:
    raise SystemExit(f"A cartilha deveria ter 1 página, mas tem {len(pdf)}: o conteúdo passou do A4.")
pdf[0].render(scale=200 / 72).to_pil().convert("RGB").save(PNG)  # 200 dpi
pdf.close()
print("OK", PNG.name, PDF.name)
