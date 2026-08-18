# Migración Odoo 17 → 18 Community — Fases 0 y 1

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development o superpowers:executing-plans. Los pasos usan checkbox (`- [ ]`).

**Goal:** repo reducido a lo que se usa, y los 28 módulos custom instalando en Odoo 18. No toca producción.

**Destino 18.0, no 19.0.** Un salto de BD en vez de dos. Los 4 módulos OCA que exige el manifest del custom existen en 18.0 y no en 19.0. El trabajo de 19 está en el backlog del final.

**Tech Stack:** Odoo 18.0 Community (`odoo:18.0`), PostgreSQL 15, Python 3.10, Docker Compose, `odoo-bin upgrade_code`.

## Global Constraints

- **No hay Odoo local en la máquina de trabajo.** Todo lo que necesite Odoo corriendo se ejecuta en el Docker del usuario.
- **Prohibido ejecutar formateadores** (`black`, `ruff format`, `prettier`). `upgrade_code` reescribe ficheros: eso es migración, no formateo. Linters sin `--fix`, sí.
- **`addons/third-party-addons/` no se modifica.** Los OCA se actualizan trayendo su rama 18.0.
- Odoo 18 exige **Python ≥ 3.10** (`MIN_PY_VERSION` en `odoo/__init__.py`). Producción ya lo cumple. PG 15 también.
- **`leulit_almacen` exige un `res_company` con `id=2`** en cualquier BD que se cree.
- Rama de trabajo: `migracion-odoo-18`. Nunca `main`.

### Lo que NO se toca, verificado contra `odoo/odoo@18.0`

| Patrón | Ocurrencias | Estado en 18.0 |
|---|---|---|
| `t-esc` / `t-raw` | 1.436 + 19 | Funcionan (`_compile_directive_esc`/`_raw` delegan en `_out`) |
| `_sql_constraints` | 4 | Funciona: 13 usos en `odoo/models.py@18.0` |
| rutas `type='json'` | 6 | Funcionan: las usa `addons/web/controllers/dataset.py@18.0` |
| `groups_id` | 69 | 18 sigue con `groups_id`. Cambio de 19 |
| `hr_contract` / `hr.expense.sheet` | módulo + 11 | Existen en 18 |
| `product_uom` | 17 | 18 sigue con `product_uom` |
| `odoo.osv` | 1 | `odoo/osv/` existe en 18 |
| imports de `odoo.models` | — | 18 mantiene `models.py`/`api.py`/`fields.py` planos |

## File Structure

| Fichero | Responsabilidad |
|---|---|
| `tools/migracion18/inventario.py` | Parsea manifests, cierre transitivo de dependencias, cruce con instalados. Lo usan las tareas 1 y 2 |
| `tools/migracion18/modulos_instalados.txt` | Lista exportada de producción |
| `tools/migracion18/test_inventario.py` | Verifica que el inventario no propone borrar nada necesario |
| `tools/migracion18/borrar_no_usados.sh` | Ejecuta el borrado |
| `tools/migracion18/limpiar_attachments_muertos.py` | Re-apunta `ir.attachment` con `res_model` inexistente |
| `docker/Dockerfile.18` + `docker/docker-compose.18.yml` + `config-18/odoo.conf` | Entorno 18 de desarrollo |
| `docs/migracion-odoo-18-hallazgos.md` | Entregable de las tareas de auditoría (4, 11, 13, 14) |
| `docs/migracion-odoo-18-permisos.md` | Matriz de permisos por rol (tarea 12) |

---

## FASE 0 — Reducir alcance

Independiente del destino: vale para 18 y para 19.

### Task 1: Inventario reproducible

**Files:** Create `tools/migracion18/inventario.py`, `modulos_instalados.txt`; Test `test_inventario.py`

**Interfaces:** `cargar_manifests(raiz) -> dict[str, dict]` con `{'depends': list, 'origen': 'custom'|'vendored'}`; `cierre_dependencias(manifests, semillas) -> set`; `clasificar(manifests, instalados) -> dict` con claves `custom`, `vendored_usados`, `vendored_borrables`, `deps_externas`. Lo consume la Task 2.

- [ ] **Step 1: Exportar los instalados desde producción**

```bash
docker exec -ti helipistas_odoo_17 odoo shell -d productiu --no-http
```

```python
mods = env['ir.module.module'].search([('state', '=', 'installed')]).mapped('name')
open('/tmp/modulos_instalados.txt', 'w').write('\n'.join(sorted(mods)))
print(len(mods), 'módulos instalados')
```

```bash
mkdir -p tools/migracion18
docker cp helipistas_odoo_17:/tmp/modulos_instalados.txt tools/migracion18/modulos_instalados.txt
wc -l tools/migracion18/modulos_instalados.txt   # esperado: ~275
```

- [ ] **Step 2: Escribir el test primero**

`tools/migracion18/test_inventario.py`:

```python
"""Comprueba que el inventario no propone borrar nada que se necesite."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from inventario import cargar_manifests, cierre_dependencias, clasificar

RAIZ = pathlib.Path(__file__).resolve().parents[2] / "addons"
INSTALADOS = pathlib.Path(__file__).parent / "modulos_instalados.txt"


def _datos():
    manifests = cargar_manifests(RAIZ)
    instalados = set(INSTALADOS.read_text().split())
    return manifests, instalados, clasificar(manifests, instalados)


def test_ningun_borrable_esta_instalado():
    _, instalados, r = _datos()
    sobra = r["vendored_borrables"] & instalados
    assert not sobra, f"propone borrar módulos instalados: {sorted(sobra)}"


def test_ningun_borrable_es_dependencia_del_custom():
    manifests, _, r = _datos()
    custom = {n for n, m in manifests.items() if m["origen"] == "custom"}
    necesarios = cierre_dependencias(manifests, custom)
    sobra = r["vendored_borrables"] & necesarios
    assert not sobra, f"propone borrar dependencias del custom: {sorted(sobra)}"


def test_las_particiones_no_se_solapan():
    manifests, _, r = _datos()
    assert not (r["vendored_usados"] & r["vendored_borrables"])
    assert r["vendored_usados"] | r["vendored_borrables"] == {
        n for n, m in manifests.items() if m["origen"] == "vendored"
    }


if __name__ == "__main__":
    test_ningun_borrable_esta_instalado()
    test_ningun_borrable_es_dependencia_del_custom()
    test_las_particiones_no_se_solapan()
    print("OK")
```

- [ ] **Step 3: Ejecutar y ver que falla**

```bash
python3 tools/migracion18/test_inventario.py
```

Esperado: `ModuleNotFoundError: No module named 'inventario'`.

- [ ] **Step 4: Escribir `inventario.py`**

```python
#!/usr/bin/env python3
"""Inventario de módulos: qué se usa, qué se puede borrar.

Un módulo vendorizado es borrable si NO está instalado en producción y NO lo
necesita (directa o transitivamente) ningún módulo custom.
"""
import argparse
import ast
import collections
import pathlib

VENDOR_DIR = "third-party-addons"
IGNORAR = {VENDOR_DIR, "__pycache__"}


def _leer_manifest(d: pathlib.Path) -> dict | None:
    for nombre in ("__manifest__.py", "__openerp__.py"):
        f = d / nombre
        if not f.exists():
            continue
        try:
            return ast.literal_eval(f.read_text(encoding="utf-8", errors="replace"))
        except (ValueError, SyntaxError):
            # Manifest no literal: no podemos confiar en sus depends.
            print(f"  AVISO: manifest no literal, depends ignoradas: {d.name}")
            return {}
    return None


def cargar_manifests(raiz: pathlib.Path) -> dict[str, dict]:
    manifests: dict[str, dict] = {}
    for base, origen in ((raiz, "custom"), (raiz / VENDOR_DIR, "vendored")):
        if not base.is_dir():
            continue
        for d in sorted(base.iterdir()):
            if not d.is_dir() or d.name in IGNORAR:
                continue
            m = _leer_manifest(d)
            if m is None:
                continue
            manifests[d.name] = {"depends": list(m.get("depends", [])), "origen": origen}
    return manifests


def cierre_dependencias(manifests: dict[str, dict], semillas) -> set[str]:
    vistos: set[str] = set()
    cola = collections.deque(semillas)
    while cola:
        n = cola.popleft()
        if n in vistos or n not in manifests:
            continue
        vistos.add(n)
        cola.extend(manifests[n]["depends"])
    return vistos


def deps_no_locales(manifests: dict[str, dict]) -> collections.Counter:
    fuera: collections.Counter = collections.Counter()
    for m in manifests.values():
        for dep in m["depends"]:
            if dep not in manifests:
                fuera[dep] += 1
    return fuera


def clasificar(manifests: dict[str, dict], instalados: set[str]) -> dict:
    custom = {n for n, m in manifests.items() if m["origen"] == "custom"}
    vendored = {n for n, m in manifests.items() if m["origen"] == "vendored"}
    usados = vendored & (cierre_dependencias(manifests, custom) | instalados)
    return {
        "custom": custom,
        "vendored_usados": usados,
        "vendored_borrables": vendored - usados,
        "deps_externas": deps_no_locales(manifests),
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--addons", default="addons", type=pathlib.Path)
    p.add_argument("--instalados", default="tools/migracion18/modulos_instalados.txt",
                   type=pathlib.Path)
    p.add_argument("--listar-borrables", action="store_true",
                   help="imprime sólo los nombres borrables, uno por línea")
    a = p.parse_args()

    manifests = cargar_manifests(a.addons)
    instalados = set(a.instalados.read_text().split())
    r = clasificar(manifests, instalados)

    if a.listar_borrables:
        print("\n".join(sorted(r["vendored_borrables"])))
        return

    print(f"custom             : {len(r['custom'])}")
    print(f"vendored usados    : {len(r['vendored_usados'])}")
    print(f"vendored borrables : {len(r['vendored_borrables'])}")
    print(f"instalados (input) : {len(instalados)}")
    print("\ndeps referenciadas y no presentes en el repo (core de Odoo), top 15:")
    for n, c in r["deps_externas"].most_common(15):
        print(f"  {n} ({c})")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Ejecutar el test y el inventario**

```bash
python3 tools/migracion18/test_inventario.py     # esperado: OK
python3 tools/migracion18/inventario.py
```

Esperado: `custom 28`, `vendored usados ≈ 80`, `vendored borrables ≈ 268`.

> Si `borrables` baja de 250 o pasa de 290, **parar**: la lista de instalados no corresponde a esta BD.

- [ ] **Step 6: Commit**

```bash
git checkout -b migracion-odoo-18
git add tools/migracion18/
git commit -m "tools: inventario reproducible de módulos usados vs borrables"
```

---

### Task 2: Borrar los vendorizados que no se usan

**Files:** Create `tools/migracion18/borrar_no_usados.sh`; Delete ~268 directorios de `addons/third-party-addons/`

- [ ] **Step 1: Escribir el script**

```bash
#!/usr/bin/env bash
# Borra los módulos vendorizados que el inventario marca como no usados.
# Sin --ejecutar sólo enseña qué haría.
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/../.." && pwd)"
VENDOR="$RAIZ/addons/third-party-addons"
EJECUTAR="${1:-}"

# Sin `mapfile`: macOS trae bash 3.2 y no lo tiene.
LISTA="$(python3 "$RAIZ/tools/migracion18/inventario.py" --listar-borrables)"

if [ -z "$LISTA" ]; then
  echo "El inventario no propone borrar nada."
  exit 0
fi

echo "Módulos a borrar: $(printf '%s\n' "$LISTA" | wc -l | tr -d ' ')"
while IFS= read -r m; do
  [ -n "$m" ] || continue
  if [ ! -d "$VENDOR/$m" ]; then
    echo "  AVISO: no existe, se ignora: $m"
    continue
  fi
  if [ "$EJECUTAR" = "--ejecutar" ]; then
    git -C "$RAIZ" rm -r -q "addons/third-party-addons/$m"
    echo "  borrado  $m"
  else
    echo "  (dry-run) borraría  $m"
  fi
done <<< "$LISTA"

[ "$EJECUTAR" = "--ejecutar" ] || printf '\nNada borrado. Repetir con: %s --ejecutar\n' "$0"
```

```bash
chmod +x tools/migracion18/borrar_no_usados.sh
```

- [ ] **Step 2: Dry-run y revisión**

```bash
./tools/migracion18/borrar_no_usados.sh | tee /tmp/borrado-dryrun.txt
grep -c 'dry-run' /tmp/borrado-dryrun.txt
```

Repasar buscando `l10n_es*`, `account_*`, `mgmtsystem*`. Si aparece algo que crees que se usa, comprobarlo contra `modulos_instalados.txt`: esa lista es la autoridad.

- [ ] **Step 3: Ejecutar**

```bash
./tools/migracion18/borrar_no_usados.sh --ejecutar
```

- [ ] **Step 4: Verificar coherencia**

```bash
python3 tools/migracion18/test_inventario.py
# La lista de deps no presentes debe contener SÓLO módulos del core de Odoo
python3 tools/migracion18/inventario.py | sed -n '/deps referenciadas/,$p'
ls addons/third-party-addons | wc -l    # esperado: ~80
```

- [ ] **Step 5: Commit**

```bash
git add -A addons/third-party-addons tools/migracion18/borrar_no_usados.sh
git commit -m "addons: retirar los ~268 módulos vendorizados sin instalar ni usar"
```

---

### Task 3: Limpiar attachments con `res_model` muerto

2.206 filas (≈7,15 GB) apuntan a modelos inexistentes.

**Files:** Create `tools/migracion18/limpiar_attachments_muertos.py`

- [ ] **Step 1: Confirmar el mapeo contra la BD**

En los cinco casos el nombre de tabla es el mismo antes y después, así que los `res_id` deberían valer — se comprueba, no se supone.

```bash
docker exec -ti helipistas_odoo_17 odoo shell -d productiu --no-http
```

```python
MAPEO = {
    'stock.production.lot':      'stock.lot',
    'leulit_checklist':          'leulit.checklist',
    'leulit_checklist_template': 'leulit.checklist_template',
    'leulit.ruta.aerovia':       'leulit.ruta_aerovia',
    'mail.channel':              'discuss.channel',
}
for muerto, vivo in MAPEO.items():
    att = env['ir.attachment'].search([('res_model', '=', muerto)])
    ids = set(att.mapped('res_id'))
    existen = set(env[vivo].browse(ids).exists().ids)
    print(f"{muerto:28} -> {vivo:26} filas={len(att):5} res_id_ok={len(ids & existen):5} huerfanos={len(ids - existen):5}")
```

> Si para algún modelo `res_id_ok` es 0, ese mapeo es falso: investigar antes de continuar.

- [ ] **Step 2: Escribir el script**

`tools/migracion18/limpiar_attachments_muertos.py`:

```python
#!/usr/bin/env python3
"""Re-apunta los ir.attachment cuyo res_model ya no existe.

Se ejecuta dentro de `odoo shell`:

    docker exec -i helipistas_odoo_17 odoo shell -d <db> --no-http \
        < tools/migracion18/limpiar_attachments_muertos.py
"""

EJECUTAR = False   # a True sólo tras revisar la salida del dry-run

MAPEO = {
    'stock.production.lot':      'stock.lot',
    'leulit_checklist':          'leulit.checklist',
    'leulit_checklist_template': 'leulit.checklist_template',
    'leulit.ruta.aerovia':       'leulit.ruta_aerovia',
    'mail.channel':              'discuss.channel',
}

Attachment = env['ir.attachment'].sudo()
total_reapuntados = total_borrados = 0

for muerto, vivo in MAPEO.items():
    att = Attachment.search([('res_model', '=', muerto)])
    if not att:
        print(f"{muerto}: 0 filas")
        continue

    if vivo is None or vivo not in env:
        print(f"{muerto}: {len(att)} filas -> BORRAR (sin modelo destino)")
        total_borrados += len(att)
        if EJECUTAR:
            att.unlink()
        continue

    vivos = set(env[vivo].browse(set(att.mapped('res_id'))).exists().ids)
    reapuntar = att.filtered(lambda a: a.res_id in vivos)
    huerfanos = att - reapuntar

    print(f"{muerto} -> {vivo}: re-apuntar {len(reapuntar)}, borrar {len(huerfanos)}")
    total_reapuntados += len(reapuntar)
    total_borrados += len(huerfanos)

    if EJECUTAR:
        if reapuntar:
            reapuntar.write({'res_model': vivo})
        if huerfanos:
            huerfanos.unlink()

print(f"\nTOTAL re-apuntados: {total_reapuntados}   borrados: {total_borrados}")
print("MODO:", "ESCRITURA" if EJECUTAR else "DRY-RUN")

if EJECUTAR:
    restantes = Attachment.search_count([('res_model', 'in', list(MAPEO))])
    assert restantes == 0, f"quedan {restantes} filas con res_model muerto"
    env.cr.commit()
    print("verificado: 0 filas con res_model muerto")
```

- [ ] **Step 3: Dry-run sobre una COPIA, nunca sobre producción**

```bash
docker exec -i helipistas_odoo_17 odoo shell -d productiu_copia --no-http \
  < tools/migracion18/limpiar_attachments_muertos.py
```

Esperado: ~2.206 filas repartidas, `MODO: DRY-RUN`.

- [ ] **Step 4: Ejecutar sobre la copia y verificar**

`EJECUTAR = True` y repetir. Esperado: la aserción no salta.

```python
print('stock.lot con adjuntos:', env['ir.attachment'].search_count([('res_model','=','stock.lot')]))
# esperado: ~1.087 + los ~1.399 re-apuntados desde stock.production.lot
```

- [ ] **Step 5: Commit del script, no de los datos**

```bash
git add tools/migracion18/limpiar_attachments_muertos.py
git commit -m "tools: script para re-apuntar attachments con res_model muerto"
```

> La ejecución contra producción va en la ventana del cutover, con backup hecho.

---

### Task 4: Diagnosticar los 13.019 attachments huérfanos

2,86 GB sin `res_model`, y `leulit/models/ir_attachment.py` sobreescribe `check()` para exponerlos a `RBase`. No se borran a ciegas.

**Files:** Create `docs/migracion-odoo-18-hallazgos.md`

- [ ] **Step 1: Quién los crea**

```bash
grep -rn --include='*.py' --exclude-dir=third-party-addons \
  -E "ir\.attachment.*\.create\(|'ir\.attachment'\]\.create\(" addons/ | tee /tmp/att-create.txt
wc -l /tmp/att-create.txt
```

Para cada resultado, comprobar si el `vals` incluye `res_model` y `res_id`.

- [ ] **Step 2: Perfilarlos**

```bash
docker exec -ti helipistas_odoo_17 odoo shell -d productiu --no-http
```

```python
from collections import Counter
att = env['ir.attachment'].sudo().search([('res_model', '=', False)])
print('total huérfanos:', len(att))
print('por año:', sorted(Counter(a.create_date.year for a in att).items()))
print('por creador:', Counter(a.create_uid.login for a in att).most_common(10))
print('por mimetype:', Counter(a.mimetype for a in att).most_common(10))
print('con res_field:', len(att.filtered('res_field')))
```

> Un attachment con `res_field` relleno y sin `res_model` suele ser respaldo de un campo binario, no basura. Ésos no se tocan.

- [ ] **Step 3: Escribir la conclusión en la bitácora**

Con la salida real de los pasos 1 y 2, y una de estas tres: respaldo de campos binarios (no se tocan), los crea el código X (se corrige y se re-apuntan), o basura histórica (se borran en el cutover con backup).

- [ ] **Step 4: Commit**

```bash
git add docs/migracion-odoo-18-hallazgos.md
git commit -m "docs: diagnóstico de los 13.019 attachments sin res_model"
```

---

## FASE 1 — Código custom sobre Odoo 18

### Task 5: Entorno Odoo 18 local

**Files:** Create `docker/Dockerfile.18`, `docker/docker-compose.18.yml`, `config-18/odoo.conf`

- [ ] **Step 1: Imagen con las deps Python de los módulos**

La imagen pelada no basta: sin estas deps los módulos no importan y el fallo sale como `ImportError`, fácil de confundir con un problema de migración.

```bash
grep -rh --include='__manifest__.py' --exclude-dir=third-party-addons \
  -A4 'external_dependencies' addons/
```

`docker/Dockerfile.18`:

```dockerfile
FROM odoo:18.0

USER root
# CLAUDE.md + external_dependencies de leulit_esignature (pyqrcode/pypng/pyotp),
# leulit_almacen (pypdf), leulit_ia (anthropic/requests), leulit_partis (dateutil)
RUN pip3 install --no-cache-dir --break-system-packages \
        pypdf pyqrcode pypng pyotp anthropic requests python-dateutil
USER odoo
```

> `--break-system-packages` hace falta por PEP 668, igual que en `dockerserver/Dockerfile`.

- [ ] **Step 2: Configuración**

`config-18/odoo.conf`:

```ini
[options]
addons_path = /mnt/extra-addons
data_dir = /var/lib/odoo
admin_passwd = admin
db_host = db18
db_port = 5432
db_user = odoo
db_password = odoo
; sin workers: en desarrollo el traceback completo vale más que el rendimiento
workers = 0
max_cron_threads = 1
log_level = info
```

`docker/docker-compose.18.yml`:

```yaml
# Aislado del stack de 17: otros volúmenes y otro puerto.
services:
  db18:
    image: postgres:15
    container_name: helipistas_db_18
    environment:
      - POSTGRES_USER=odoo
      - POSTGRES_PASSWORD=odoo
      - POSTGRES_DB=postgres
      - PGDATA=/var/lib/postgresql/data/pgdata
    volumes:
      - db-data-odoo18:/var/lib/postgresql/data/pgdata

  odoo18:
    build:
      context: .
      dockerfile: Dockerfile.18
    container_name: helipistas_odoo_18
    depends_on:
      - db18
    ports:
      - "8071:8069"
    volumes:
      - web-data-odoo18:/var/lib/odoo
      - ../config-18:/etc/odoo
      - ../addons:/mnt/extra-addons
    command: odoo -c /etc/odoo/odoo.conf

volumes:
  db-data-odoo18:
  web-data-odoo18:
```

- [ ] **Step 3: Levantar y verificar**

```bash
cd docker && docker compose -f docker-compose.18.yml up -d --build
docker logs -f helipistas_odoo_18      # hasta "HTTP service (werkzeug) running on"

docker exec helipistas_odoo_18 odoo --version        # esperado: Odoo Server 18.0
docker exec helipistas_odoo_18 python3 --version     # >= 3.10
docker exec helipistas_odoo_18 python3 -c \
  "import pypdf, pyqrcode, png, pyotp, anthropic, requests, dateutil; print('deps OK')"
```

- [ ] **Step 4: Commit**

```bash
git add docker/Dockerfile.18 docker/docker-compose.18.yml config-18/odoo.conf
git commit -m "docker: stack de desarrollo Odoo 18 aislado del de 17"
```

---

### Task 6: `<tree>` → `<list>` con `upgrade_code`

258 ocurrencias en 151 ficheros.

**Files:** Modify ~151 `.xml`

- [ ] **Step 1: Ver los scripts de la imagen**

```bash
docker exec helipistas_odoo_18 ls /usr/lib/python3/dist-packages/odoo/upgrade_code/
```

Esperado: sólo `17.5-00-example.py` y `17.5-01-tree-to-list.py`. Los `18.1-*` y `18.5-*` son cambios posteriores a 18.0, o sea trabajo de 19.

- [ ] **Step 2: Dry-run**

```bash
docker exec helipistas_odoo_18 odoo upgrade_code \
  --script 17.5-01-tree-to-list.py \
  --addons-path /mnt/extra-addons \
  --dry-run 2>&1 | tee /tmp/upgrade-code-dryrun.txt
grep -c 'third-party-addons' /tmp/upgrade-code-dryrun.txt
```

El grep debe dar **0**. Si da más, acotar `--addons-path` a un directorio con sólo los custom.

- [ ] **Step 3: Ejecutar**

```bash
docker exec helipistas_odoo_18 odoo upgrade_code \
  --script 17.5-01-tree-to-list.py --addons-path /mnt/extra-addons
```

- [ ] **Step 4: Verificar, incluidos los `view_mode`**

```bash
grep -rIl --exclude-dir=third-party-addons --include='*.xml' -E '<tree[ >]' addons/ | wc -l   # 0
grep -rIn --exclude-dir=third-party-addons --include='*.xml' -E 'view_mode="[^"]*tree' addons/
```

Si el segundo devuelve algo, corregir `tree` → `list` a mano en este mismo commit.

- [ ] **Step 5: Commit**

```bash
git add -A addons
git commit -m "migracion18: <tree> -> <list> via upgrade_code 17.5-01"
```

---

### Task 7: `oe_chatter` → `<chatter/>`

31 ocurrencias en 30 ficheros.

**Files:** Modify 30 `.xml`

- [ ] **Step 1: Ver la forma a sustituir**

```bash
grep -rIn -A4 --exclude-dir=third-party-addons --include='*.xml' 'oe_chatter' addons/ | head -40
```

El patrón de 17 es un `<div class="oe_chatter">` con `message_follower_ids`, `activity_ids` y `message_ids`; en 18 se sustituye entero por `<chatter/>`.

- [ ] **Step 2: Sustituir**

El bloque ocupa varias líneas, así que `sed` no sirve:

```bash
python3 - <<'PY'
import pathlib, re

RE = re.compile(r'([ \t]*)<div class="oe_chatter">.*?</div>[ \t]*\n?', re.DOTALL)
tocados = 0
for f in pathlib.Path('addons').rglob('*.xml'):
    if 'third-party-addons' in f.parts:
        continue
    t = f.read_text(encoding='utf-8')
    if 'oe_chatter' not in t:
        continue
    nuevo, n = RE.subn(lambda m: f'{m.group(1)}<chatter/>\n', t)
    if n:
        f.write_text(nuevo, encoding='utf-8')
        tocados += 1
        print(f'{f}: {n} bloque(s)')
print('ficheros tocados:', tocados)
PY
```

- [ ] **Step 3: Verificar que no se perdió contenido**

```bash
grep -rIl --exclude-dir=third-party-addons --include='*.xml' 'oe_chatter' addons/ | wc -l   # 0
grep -rIl --exclude-dir=third-party-addons --include='*.xml' '<chatter/>' addons/ | wc -l   # ~30
```

El regex se come todo lo que hubiera dentro del div. Si alguno tenía algo más que los tres campos estándar, aparecerá aquí:

```bash
git diff -- '*.xml' | grep -E '^-' \
  | grep -vE 'message_follower_ids|activity_ids|message_ids|oe_chatter|</div>|^---' | head
```

Esperado: vacío. Cualquier línea es contenido perdido que hay que restaurar.

- [ ] **Step 4: Commit**

```bash
git add -A addons && git commit -m "migracion18: div.oe_chatter -> <chatter/>"
```

---

### Task 8: `name_get` → `_compute_display_name`

`name_get` desaparece en 18 (1 uso en `odoo/models.py@17.0`, 0 en 18.0). Hay 1 definición y 3 usos en el custom.

**Files:** Modify 3 `.py`

- [ ] **Step 1: Localizar**

```bash
grep -rIn --exclude-dir=third-party-addons --include='*.py' 'name_get' addons/
```

- [ ] **Step 2: Convertir**

El proyecto ya usa el patrón de destino en 8 ficheros (16 veces):

```python
@api.depends('codigo', 'matricula')
def _compute_display_name(self):
    for rec in self:
        rec.display_name = f"{rec.codigo} - {rec.matricula}"
```

Dos cuidados:

- **El `@api.depends` es obligatorio** y debe listar todos los campos que use el cuerpo. Si falta uno, el nombre se queda obsoleto en pantalla sin dar error.
- Los usos `rec.name_get()[0][1]` pasan a `rec.display_name`.

- [ ] **Step 3: Verificar**

```bash
grep -rIn --exclude-dir=third-party-addons --include='*.py' 'name_get' addons/ | wc -l   # 0
docker exec helipistas_odoo_18 python3 -m compileall -q /mnt/extra-addons && echo compila
```

- [ ] **Step 4: Commit**

```bash
git add -A addons
git commit -m "migracion18: name_get -> _compute_display_name (eliminado en 18)"
```

---

### Task 9: `kanban-box` → `card`, y restos de `attrs`/`states`

**Files:** Modify 6 `.xml` (`kanban-box`), 1 (`attrs=`), 1 (`states=`)

- [ ] **Step 1: Localizar**

```bash
grep -rIn --exclude-dir=third-party-addons -E 'kanban-box|kanban_box' addons/
grep -rIn --exclude-dir=third-party-addons --include='*.xml' -E 'attrs=|\bstates=' addons/
```

- [ ] **Step 2: Sustituir**

Comprobar la forma real en el core antes de escribirla:

```bash
docker exec helipistas_odoo_18 grep -rn 'class="card' \
  /usr/lib/python3/dist-packages/odoo/addons/maintenance/views/maintenance_views.xml | head -3
```

`attrs=` (2) y `states=` (4) pasan a atributos directos: `invisible=`, `readonly=`, `required=` con expresión de dominio.

- [ ] **Step 3: Verificar**

```bash
for p in 'kanban-box' 'attrs=' '\bstates='; do
  printf '%-14s %s\n' "$p" "$(grep -rIh --exclude-dir=third-party-addons -oE "$p" addons/ | wc -l | tr -d ' ')"
done
```

Esperado: 0 en los tres.

- [ ] **Step 4: Commit**

```bash
git add -A addons
git commit -m "migracion18: kanban-box -> card y restos de attrs/states"
```

---

### Task 10: Instalar los 28 módulos custom en Odoo 18

Primer momento de verdad: hasta aquí sólo se ha reescrito texto.

**Files:** Modify lo que la instalación rompa

- [ ] **Step 1: Pasar los OCA que quedan a su rama 18.0**

No se reescriben: se sustituyen por la rama 18.0 de su repo.

```bash
python3 - <<'PY'
import ast, pathlib
raiz = pathlib.Path('addons/third-party-addons')
for d in sorted(raiz.iterdir()):
    m = d / '__manifest__.py'
    if not m.exists():
        continue
    try:
        v = ast.literal_eval(m.read_text()).get('version', '?')
    except Exception:
        v = 'ILEGIBLE'
    if not str(v).startswith('18.'):
        print(f'{d.name:40} {v}')
PY
```

Los que no tengan 18.0 son los bloqueantes conocidos: MuK (5), Odoo Mates (8), `base_bank_from_iban` y `base_iso3166`. Los 4 que exige el manifest del custom **sí** están en 18.0: `maintenance_equipment_hierarchy`, `maintenance_equipment_sequence`, `project_status`, `project_timesheet_time_control`.

- [ ] **Step 2: BD de prueba con la compañía `id=2`**

```bash
docker exec helipistas_odoo_18 odoo -d test18 -i base --stop-after-init
docker exec -ti helipistas_odoo_18 odoo shell -d test18 --no-http
```

```python
if not env['res.company'].browse(2).exists():
    env['res.company'].create({'name': 'Helipistas 2'})
print('company id=2:', env['res.company'].browse(2).exists() and env['res.company'].browse(2).name)
env.cr.commit()
```

- [ ] **Step 3: Instalar el módulo base del proyecto**

```bash
docker exec -ti helipistas_odoo_18 odoo -d test18 -i leulit --stop-after-init 2>&1 | tail -40
```

Arreglar lo que salga y repetir hasta que instale limpio. Fallos esperables: campos renombrados y vistas que no validan.

- [ ] **Step 4: El resto, de menos a más dependiente**

```bash
for m in leulit_actividad leulit_operaciones leulit_taller leulit_actividad_taller \
         leulit_camo leulit_parte_145 leulit_escuela leulit_seguridad leulit_calidad \
         leulit_almacen leulit_planificacion leulit_comercial leulit_combustible \
         leulit_encuestas leulit_tarea leulit_esignature leulit_meteo \
         leulit_groups_manager leulit_hide_menus leulit_trabajador_externo \
         leulit_user_impersonate leulit_crm_team leulit_activity_date_history \
         maintenance_equipment_changes leulit_partis leulit_nda leulit_ia; do
  echo "=== $m"
  docker exec helipistas_odoo_18 odoo -d test18 -i "$m" --stop-after-init 2>&1 | tail -6
done
```

- [ ] **Step 5: Verificar que están los 28**

```bash
docker exec -ti helipistas_odoo_18 odoo shell -d test18 --no-http
```

```python
inst = env['ir.module.module'].search([
    ('state', '=', 'installed'),
    '|', ('name', '=like', 'leulit%'), ('name', '=', 'maintenance_equipment_changes'),
])
print(f'instalados: {len(inst)} de 28')
assert len(inst) == 28, f"faltan módulos: {sorted(inst.mapped('name'))}"
```

- [ ] **Step 6: Commit**

```bash
git add -A addons
git commit -m "migracion18: los 28 módulos custom instalan en Odoo 18"
```

---

### Task 11: Auditar el SQL crudo

53 `.execute(` en 29 ficheros. No dan error de compilación: si una tabla cambió de nombre, fallan en ejecución o devuelven datos incorrectos.

**Files:** Modify `docs/migracion-odoo-18-hallazgos.md` y los ficheros que marque la auditoría

- [ ] **Step 1: Extraer consultas y tablas**

```bash
grep -rIn -A6 --exclude-dir=third-party-addons --include='*.py' -E '\.execute\(' addons/ \
  | tee /tmp/sql-crudo.txt
grep -c '\.execute(' /tmp/sql-crudo.txt   # esperado: 53

grep -rIhoE 'FROM +[a-z_]+|JOIN +[a-z_]+|UPDATE +[a-z_]+|INTO +[a-z_]+' /tmp/sql-crudo.txt \
  | awk '{print tolower($2)}' | sort -u | tee /tmp/sql-tablas.txt
```

- [ ] **Step 2: Comprobar cada tabla contra el esquema real de 18**

`hr_contract` y `hr_expense_sheet` **siguen existiendo en 18**, así que el SQL que las use no se rompe ahora — sí en 19.

```bash
docker exec -ti helipistas_db_18 psql -U odoo -d test18 -c "\dt" > /tmp/tablas18.txt
while read -r t; do
  grep -qw "$t" /tmp/tablas18.txt && echo "  OK      $t" || echo "  AUSENTE $t"
done < /tmp/sql-tablas.txt
```

- [ ] **Step 3: Anotar y corregir**

Tabla en la bitácora con fichero:línea, tabla, veredicto (`OK` / `ROTO` / `ROTO-EN-19`) y acción. Corregir los `ROTO`; los `ROTO-EN-19` se dejan funcionando pero anotados.

Donde el SQL crudo exista sólo por rendimiento y el ORM baste, pasarlo al ORM sale más barato que volver a auditarlo en 19.

- [ ] **Step 4: Commit**

```bash
git add -A addons docs/migracion-odoo-18-hallazgos.md
git commit -m "migracion18: auditoría del SQL crudo contra el esquema de 18"
```

---

### Task 12: Matriz de permisos por rol

En 18 `groups_id` no cambia, así que esta tarea es menor que en 19 — pero hay 229 `.sudo()` y una jerarquía de roles que no falla en voz alta, y ahora se puede comprobar de verdad porque los módulos instalan.

**Files:** Create `docs/migracion-odoo-18-permisos.md`

- [ ] **Step 1: Listar los roles reales**

```bash
grep -oE 'id="R[A-Za-z_]+"' addons/leulit/groups.xml | sed 's/id="//;s/"//' | sort -u
```

- [ ] **Step 2: Construir la matriz esperada**

Una fila por rol, una columna por área (vuelos, taller/CAMO, escuela, seguridad/calidad, almacén, contabilidad), y en cada celda `-`, `R`, `RW` o `RWD`. Fuente: el `ir.model.access.csv` de cada módulo más `groups.xml`. Donde no esté claro, se pregunta.

- [ ] **Step 3: Auditar los `.sudo()`**

```bash
grep -rIn --exclude-dir=third-party-addons --include='*.py' '\.sudo\(' addons/ | tee /tmp/sudo.txt
wc -l /tmp/sudo.txt   # esperado: 229
```

Clasificar cada uno: **necesario** (datos del sistema, cron, multi-compañía) o **atajo** (puesto para saltar un permiso mal configurado). Los atajos se anotan aunque en 18 no cambien de comportamiento: son lo que morderá en 19.

- [ ] **Step 4: Verificar contra la instalación real**

```bash
docker exec -ti helipistas_odoo_18 odoo shell -d test18 --no-http
```

```python
for xmlid in ['leulit.ROperaciones_piloto', 'leulit.ROperaciones_responsable',
              'leulit.RBase_employee']:
    g = env.ref(xmlid)
    u = env['res.users'].create({
        'name': f'test {g.name}', 'login': f'test_{g.id}',
        'groups_id': [(6, 0, [env.ref("base.group_user").id, g.id])],
    })
    print(xmlid, '->', u.login)
env.cr.commit()
```

Entrar con cada uno en `http://localhost:8071` y recorrer la matriz. Lo que no se comprueba aquí se descubre en producción.

- [ ] **Step 5: Commit**

```bash
git add docs/migracion-odoo-18-permisos.md
git commit -m "docs: matriz de permisos por rol y auditoría de los 229 sudo()"
```

---

### Task 13: Auditar los `patch()` de JavaScript

El frontend está sano (0 `odoo.define`, 0 `@web/legacy`, 18 `@odoo-module`), pero 10 `patch()` tocan internals del web client, que cambió en 18. No fallan en compilación.

**Files:** Modify los `.js` con `patch()` y la bitácora

- [ ] **Step 1: Localizar**

```bash
grep -rIn --exclude-dir=third-party-addons --include='*.js' -B3 '\bpatch(' addons/ | tee /tmp/patches.txt
grep -c '\bpatch(' /tmp/patches.txt   # esperado: 10
```

- [ ] **Step 2: Comprobar que el objetivo existe en 18**

```bash
docker exec helipistas_odoo_18 find \
  /usr/lib/python3/dist-packages/odoo/addons/web/static/src -name '*.js' \
  | xargs grep -ln 'class ListRenderer' | head
```

Verificar módulo, clase y método de cada patch.

- [ ] **Step 3: Verificar en el navegador**

Abrir `http://localhost:8071`, entrar en las vistas afectadas y mirar la consola. Un `patch()` contra algo inexistente da `TypeError: Cannot read properties of undefined` en carga, no un error de servidor.

Sospechoso directo: `leulit/static/src/js/widget_semaforo_field.js`, que usa la API de campos de OWL.

- [ ] **Step 4: Anotar y corregir**

Para cada patch: `OK`, `re-apuntado`, o `ya no hace falta` (si 18 trae de serie lo que añadía).

- [ ] **Step 5: Commit**

```bash
git add -A addons docs/migracion-odoo-18-hallazgos.md
git commit -m "migracion18: auditoría de los 10 patch() de OWL contra el web client de 18"
```

---

### Task 14: Auditar los hilos con cursor propio

73 usos de `threading` en 42 ficheros. El patrón está en `addons/leulit/models/res_partner.py` (`_recalcular_complete_name_thread`). En 18 el ORM no se reestructura, pero el patrón toca `registry`/`sql_db` y falla en segundo plano.

**Files:** Modify los ficheros que marque la auditoría y la bitácora

- [ ] **Step 1: Localizar**

```bash
grep -rIn --exclude-dir=third-party-addons --include='*.py' \
  -E 'import threading|Thread\(|threading\.' addons/ | tee /tmp/threads.txt
wc -l /tmp/threads.txt    # ~73

grep -rIn --exclude-dir=third-party-addons --include='*.py' \
  -E 'registry\(|Environment\(|with_env\(|db_connect|cr\.commit\(\)' addons/ | tee /tmp/threads-cursor.txt
```

- [ ] **Step 2: Comprobar que la API existe en 18**

```bash
docker exec helipistas_odoo_18 python3 -c "
import odoo, odoo.sql_db
from odoo.modules.registry import Registry
from odoo.api import Environment
print('Registry OK:', Registry)
print('Environment OK:', Environment)
print('db_connect OK:', odoo.sql_db.db_connect)
"
```

- [ ] **Step 3: Probar el hilo de verdad**

No basta con que importe. En `test18`:

```python
p = env['res.partner'].search([], limit=1)
p.recalcular_complete_name_async()
# docker logs --tail 50 helipistas_odoo_18
```

Un hilo con cursor mal manejado no da error en la petición: deja una transacción colgada o una excepción en el log.

- [ ] **Step 4: Anotar**

Para cada hilo: qué hace, si sigue haciendo falta un hilo (Odoo tiene cron) y si el cursor sobrevive. Donde un `ir.cron` haga lo mismo, **proponerlo pero no hacerlo aquí**: cambiar concurrencia y migrar de versión a la vez impide saber qué rompió qué.

- [ ] **Step 5: Commit**

```bash
git add -A addons docs/migracion-odoo-18-hallazgos.md
git commit -m "migracion18: auditoría de los hilos con cursor propio contra el ORM de 18"
```

---

### Task 15 (opcional): `create()` de un registro → `@api.model_create_multi`

**No hace falta para 18:** `odoo/api.py@18.0` conserva `model_create_single` y auto-envuelve un `def create(self, vals)`. Los 18 ficheros funcionan tal cual. Se incluye porque es trabajo de 19 que sale barato ahora. Si el calendario aprieta, se salta.

**Files:** Modify los 18 ficheros con `def create(self, vals)`

- [ ] **Step 1: Localizar**

```bash
grep -rIn --exclude-dir=third-party-addons --include='*.py' \
  -E 'def create\(self, ?vals\)' addons/ | tee /tmp/create-single.txt
wc -l /tmp/create-single.txt   # esperado: 18
```

- [ ] **Step 2: Convertir**

```python
# Antes
@api.model
def create(self, vals):
    vals['codigo'] = self.env['ir.sequence'].next_by_code('leulit.vuelo')
    return super().create(vals)

# Después
@api.model_create_multi
def create(self, vals_list):
    for vals in vals_list:
        vals['codigo'] = self.env['ir.sequence'].next_by_code('leulit.vuelo')
    return super().create(vals_list)
```

Dos trampas:

- **`return` dentro del cuerpo:** al meterlo en el bucle sólo procesa el primer elemento. Hay que reestructurar, no envolver.
- **Trabajo posterior al `super()`** que asuma un único registro (`res.campo = ...`): con varios hay que iterar el recordset devuelto.

- [ ] **Step 3: Verificar**

```bash
grep -rIn --exclude-dir=third-party-addons --include='*.py' \
  -E 'def create\(self, ?vals\)' addons/ | wc -l   # 0
docker exec helipistas_odoo_18 odoo -d test18 -u all --stop-after-init 2>&1 | tail -20
```

La actualización de todos los módulos es la prueba real: un `create` mal convertido revienta al cargar datos.

- [ ] **Step 4: Commit**

```bash
git add -A addons
git commit -m "migracion18: create() de un registro -> @api.model_create_multi (adelanto de 19)"
```

---

## Criterio de salida

1. `ls addons/third-party-addons | wc -l` da ~80 y `test_inventario.py` pasa.
2. Los greps de las tareas 6, 7, 8 y 9 dan 0.
3. **Los 28 módulos custom instalan en Odoo 18** (Task 10 paso 5: la aserción pasa).
4. Las deps Python importan en el contenedor (Task 5 paso 3).
5. `docs/migracion-odoo-18-hallazgos.md` relleno con las tareas 4, 11, 13 y 14, y `docs/migracion-odoo-18-permisos.md` con la 12, incluida la comprobación por rol.
6. El script de attachments probado sobre una copia, con su aserción en verde.

---

## Backlog del salto 18 → 19

Trabajo medido que este destino aplaza a propósito.

| Trabajo | Volumen | Por qué se aplaza |
|---|---|---|
| `groups_id` → `group_ids` + `all_group_ids` | 69 usos / 15 ficheros | 18 conserva `groups_id`. Es el mayor riesgo del proyecto (fallo silencioso de permisos); aislarlo permite atribuir los fallos |
| `res.groups.privilege` (modelo nuevo) | 104 usos de `res.groups` | Sólo existe en 19 |
| `hr_contract` → `hr.version` dentro de `hr` | módulo instalado | 18 lo conserva |
| `hr.expense.sheet` eliminado | 11 usos / 4 ficheros + 1.885 adjuntos | 18 conserva el modelo |
| `product_uom` → `product_uom_id` | 17 / 7 ficheros | 18 conserva `product_uom` |
| `_sql_constraints` → `models.Constraint` | 4 | Cambio de 18.1+; automatizable con `18.1-00-sql-constraint.py` |
| rutas `type='json'` → `'jsonrpc'` | 6 / 3 ficheros | Cambio de 18.1+; automatizable con `18.1-02-route-jsonrpc.py` |
| Imports profundos de `odoo.models` / `odoo.osv` | 1 confirmado, resto a medir | 19 los convierte en paquetes y añade `odoo/orm/` |
| Re-migrar los vendorizados a 19.0 | ~80 módulos | OCA 19.0 tenía 864 módulos frente a 1.938 en 18.0 el 2026-08-17. Re-medir |
| MuK a 19 | 5 módulos / 2.321 líneas | En 18 hay port comunitario de referencia; para 19 no |
| `t-esc` / `t-raw` → `t-out` | 1.436 + 19 | Funcionan en 18 y en 19. Nunca urgente |
