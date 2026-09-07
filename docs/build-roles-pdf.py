"""Genera docs/roles-autorizaciones.pdf = resumen visual + anexo tecnico.

Fuentes: docs/roles-organigrama.html (visual) + docs/roles-autorizaciones.md (detalle).
Uso: python3 docs/build-roles-pdf.py
"""
import re, subprocess, pathlib

root = pathlib.Path(__file__).resolve().parent.parent
visual = (root / "docs/roles-organigrama.html").read_text(encoding="utf-8")

anexo = subprocess.run(
    ["pandoc", "-f", "markdown", "-t", "html5", str(root / "docs/roles-autorizaciones.md")],
    capture_output=True, text=True, check=True,
).stdout

# el anexo repite portada y metadatos: se recorta desde el primer <h2>
i = anexo.find("<h2")
if i > 0:
    anexo = anexo[i:]

extra_css = """
  .anexo { page-break-before: always; }
  .anexo h1 { font-size: 15pt; color:#0f1b2d; margin:0 0 1mm; font-weight:700; }
  .anexo h2 { font-size: 12pt; color:#0f1b2d; margin:7mm 0 2mm; font-weight:700;
              border-bottom:1px solid #dde2e9; padding-bottom:1.5mm; page-break-after:avoid; }
  .anexo h3 { font-size: 10pt; color:#1f4e7a; margin:5mm 0 1.5mm; font-weight:650; page-break-after:avoid; }
  .anexo h4 { font-size: 9pt; color:#0f1b2d; margin:3.5mm 0 1mm; font-weight:650; page-break-after:avoid; }
  .anexo p  { margin:0 0 2mm; font-size:8.5pt; color:#333d4d; }
  .anexo ul, .anexo ol { margin:0 0 2.5mm; padding-left:5mm; font-size:8.5pt; color:#333d4d; }
  .anexo li { margin-bottom:1mm; }
  .anexo li p { margin:0; }
  .anexo code { background:#eef1f4; padding:.4mm 1.2mm; border-radius:2px; font-size:7.8pt; color:#1f4e7a; }
  .anexo pre { background:#f7f8fa; border:1px solid #e3e7ec; border-radius:3px;
               padding:2.5mm 3mm; overflow-x:hidden; page-break-inside:avoid; }
  .anexo pre code { background:none; padding:0; color:#4a5566; }
  .anexo hr { border:0; border-top:1px solid #dde2e9; margin:6mm 0; }
  .anexo strong { color:#0f1b2d; }
  .anexo blockquote { margin:0 0 2mm; padding-left:3mm; border-left:2px solid #dde2e9; color:#5b6675; }
  .anexo-head { page-break-before: always; padding-top:2mm; }
  .anexo-head .kicker { font-size:8pt; letter-spacing:.16em; text-transform:uppercase; color:#7d8797; }
  .anexo-head h1 { font-size:22pt; color:#0f1b2d; margin:2mm 0 3mm; font-weight:700; letter-spacing:-.02em; }
  .anexo-head p { font-size:9pt; color:#5b6675; margin:0 0 6mm; max-width:150mm; }
"""

portada = """
<div class="anexo-head">
  <div class="kicker">Anexo técnico</div>
  <h1>Detalle de la propuesta</h1>
  <p>Catálogo completo de puestos y capacidades con sus identificadores, matriz de asignación,
  reglas de alcance a implementar y plan de despliegue. Es la referencia de trabajo para IT y
  para la validación por Control de Conformidad.</p>
</div>
"""

out = visual.replace("</style>", extra_css + "</style>")
out = out.replace("</body>", f'<div class="anexo">{portada}{anexo}</div>\n</body>')
(root / "docs/.roles-combined.html").write_text(out, encoding="utf-8")
print("HTML combinado listo")

# --- impresion a PDF ---
combined = root / "docs/.roles-combined.html"
pdf = root / "docs/roles-autorizaciones.pdf"
chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={pdf}", f"file://{combined}"],
               check=True, capture_output=True)
combined.unlink()
print(subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout.split("Pages:")[1].split("\n")[0].strip(), "paginas ->", pdf)
