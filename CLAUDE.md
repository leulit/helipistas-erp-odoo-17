# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Odoo 17 ERP for Helipistas, a helicopter operator (flights, maintenance/CAMO, flight school, safety/quality, warehouse). Custom business logic lives in `leulit_*` addons on top of stock Odoo; `addons/third-party-addons/` vendors ~350 OCA/community modules (don't modify).

For exhaustive generic Odoo/Python conventions (ORM performance rules, SOLID mapping to Odoo, controller/security patterns, OWL basics) see `.github/copilot-instructions.md` — this file only covers what's specific to this repo.

## No local Odoo instance

There is no Odoo/Postgres running in this dev environment — you cannot execute `odoo-bin`, hit the HTTP/JSON-RPC API, or run module tests here. After making changes, give the user exact, copy-pasteable commands to run and verify in their own Docker test environment (see Commands below).

## Commands

Local dev stack (`docker/docker-compose.yml`, config `config/odoo.conf`, db `productiu`, http `localhost:8070`):

```bash
cd docker && docker-compose up -d
docker logs -f helipistas_odoo_17
docker exec -ti helipistas_odoo_17 /bin/bash
```

Update/install a module against a database:

```bash
docker exec -ti helipistas_odoo_17 odoo -u <module> -d <db> --stop-after-init
docker exec -ti helipistas_odoo_17 odoo -i <module> -d <db> --stop-after-init
```

Run tests (tests live under `<module>/tests/`, using `odoo.tests.common.TransactionCase`/`HttpCase`):

```bash
docker exec -ti helipistas_odoo_17 odoo -u <module> -d <db> --test-enable --test-tags=<tag> --stop-after-init
```

Extra Python deps expected inside the Odoo container: `pypdf`, `pyqrcode`, `pypng`, `pyotp`.

## Environments — don't confuse these

- `config/odoo.conf` / `config-test/odoo.conf` — dev/test Odoo config, mounted by `docker/docker-compose.yml`.
- `docker/docker-compose.yml` — **local dev only** (named Docker volumes, no nginx).
- `dockerserver/` (`docker-compose.yml` + `Dockerfile`) — **production** deploy definition (EC2 + EFS at `/efs/HELIPISTAS-ODOO-17/`, nginx + certbot). Full server layout, container list, and deployment steps: `docs/produccion.md`.

## Architecture

### Module layout

```
addons/
  leulit/              foundation module — every leulit_* module depends on it
  leulit_*/             functional modules: operaciones, actividad(_taller), taller, camo,
                         parte_145, escuela, calidad, seguridad, almacen, comercial,
                         planificacion, esignature, meteo, nda, ia, encuestas, crm_team,
                         groups_manager, hide_menus, trabajador_externo, user_impersonate...
  third-party-addons/  OCA/community modules, vendored — don't modify
```

### `leulit` — foundation module

- `utilitylib.py`: shared constants/helpers — role names, date/time format constants, per-helicopter-model fuel densities. Import it (`from odoo.addons.leulit import utilitylib`) rather than redefining constants locally.
- `groups.xml`: hierarchical role system built with `implied_ids`, e.g. `RBase → RBase_employee → RBase_hide`, `ROperaciones_piloto_externo → ROperaciones_alumno → ROperaciones_operador → ROperaciones_piloto → ROperaciones_responsable`. New groups go here, not under a module's `security/`.
- Each module still keeps its own `security/ir.model.access.csv` for CRUD grants per group.
- `models/ir_attachment.py` overrides `check()` so `RBase` users can access orphan attachments (no `res_model`/`res_id`). When creating attachments programmatically, always set `res_model`/`res_id` explicitly.
- `static/src/js/widget_semaforo_field.js` + matching XML template: reusable OWL "semaforo" (red/amber/green) widgets for char/boolean fields (`widget="semaforo_char"`, `widget="semaforo_bool"`). A module using them must add both files under its own `assets.web.assets_backend` in `__manifest__.py`.

### View inheritance

Views are never copy-pasted; every customization is `inherit_id` + `<xpath>`. Reference example: `addons/leulit_actividad/views/leulit_vuelo.xml`.

### Key domain workflows

- **Flights** (`leulit.vuelo`, in `leulit_actividad`/`leulit_operaciones`): states `prevuelo → cerrado → cancelado`; `checkValidCreateWriteData()` validates helicopter/pilot schedule overlap; dynamic role profiles `PV_PILOTO`, `PV_ALUMNO`, `PV_INSTRUCTOR`, `PV_VERIFICADO`; post-processing hooks `vuelo_chain_postvuelo`, `vuelo_chain_cerrado`. Codes generated via `ir.sequence` (`leulit.vuelo`).
- **E-signature** (`leulit_esignature`): a `TransientModel` wizard signs records with a QR code (`pyqrcode`) + OTP (`res.users.get_otp()`); used for anomalías, vuelos, partes de escuela.
- **Warehouse location axis** (`leulit_almacen`): `stock.location` in the ICA tree is **not
  geography, it is Part-145 material state** (`Material Nuevo`, `Material Útil`, `Material
  Pendiente Decisión`, `Herramientas`, `Equipamientos`). ~36 literal name comparisons across
  8 files depend on it (the 4 move wizards, `stock_lot._get_location_stock`,
  `stock_move_line._get_tipo_instalacion`, `stock_picking`) — none use `child_of`. Never hang
  sub-locations off that tree. Physical position is a **separate axis**: caja =
  `stock.quant.package` + `estanteria_id` → `stock.location` with `usage='view'` under a
  **per-company root** — `Estanterías Icarus` (company 2) and `Estanterías Helipistas`
  (company 1); the two warehouses are separate. Odoo forbids stock in `view` locations, see
  `stock.quant.check_location_id`. The roots are resolved by xmlid, never by name
  (`stock_quant_package._raices_estanterias`), and `stock_location.unlink()` refuses to delete
  them: `location_id` is `ondelete='cascade'`, so deleting a root would wipe the whole shelf
  catalogue. Full design: `docs/cajas-estanterias.md`.
- **AI assistant** (`leulit_ia`): has its own `CLAUDE.md`/`ARCHITECTURE.md` — read those before touching this module. Summary: OWL chat sidebar in Odoo → `/ai/chat` controller → external `ai-service`/`helipistas-mcp`/`litellm-proxy` Docker containers, provider-agnostic (Claude/Ollama/Gemini via one config line). Non-negotiable rule: a feature only belongs here if it improves the user's actual daily work — no AI for AI's sake. Odoo 17 **Community** only — never reference Enterprise-only models/modules (`sign`, `documents`, `web_gantt`, `web_studio`, ...).

### Repo-specific conventions

- Long-running work runs in a background thread with its own cursor/env rather than blocking the request — pattern: `addons/leulit/models/res_partner.py` (`_recalcular_complete_name_thread` / `recalcular_complete_name_async`).
- `leulit_almacen` requires a `res_company` record with `id=2` to exist post-migration/install.
- Multi-company logic must consider `self.env.company`.

## Data migrations

Importing/migrating production data requires temporarily dropping a long list of FK/unique constraints, re-adding them afterward, backfilling `leulit_weight_and_balance.vuelo_id`, and a `company_id` `1`→`2` find/replace across custom XML data — full SQL and the field list are in `README.md`. Don't attempt this against a live system without walking the user through those steps first.
