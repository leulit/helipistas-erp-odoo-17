# Revisión de módulos — lista de seguimiento

Checklist para la revisión de módulos propios en busca de optimizaciones o
errores. Solo módulos custom (`addons/leulit_*` + `maintenance_equipment_changes`);
`addons/third-party-addons/` queda fuera — son ~350 módulos OCA vendorizados,
no se modifican (ver CLAUDE.md).

Marcar `[x]` al terminar la revisión de cada módulo. Añadir fecha y hallazgos
en la columna de notas.

- [x] leulit — 2026-09-10: 3 críticos, 4 altos, 10 medios, 4 bajos. Ver `addons/leulit/PLAN_REVISION.md`.
- [x] leulit_actividad — 2026-09-10: 7 críticos, 7 altos, 10 medios, 5 bajos. Ver `addons/leulit_actividad/PLAN_REVISION.md`.
- [x] leulit_actividad_taller — 2026-09-10: 1 crítico, 6 altos, 5 medios, 5 bajos. Ver `addons/leulit_actividad_taller/PLAN_REVISION.md`.
- [x] leulit_activity_date_history — 2026-09-10: 2 críticos, 2 altos, 3 medios, 2 bajos. Ver `addons/leulit_activity_date_history/PLAN_REVISION.md`.
- [x] leulit_almacen — 2026-09-10: 2 críticos, 8 altos, 6 medios, 4 bajos. Ver `addons/leulit_almacen/PLAN_REVISION.md`.
- [x] leulit_calidad — 2026-09-10: 2 críticos, 2 altos, 6 medios, 6 bajos. Ver `addons/leulit_calidad/PLAN_REVISION.md`.
- [x] leulit_camo — 2026-09-10: 1 crítico, 3 altos, 2 medios, 3 bajos. Ver `addons/leulit_camo/PLAN_REVISION.md`.
- [x] leulit_combustible — 2026-09-10: 3 críticos, 3 altos, 5 medios, 4 bajos. Ver `addons/leulit_combustible/PLAN_REVISION.md`.
- [x] leulit_comercial — 2026-09-10: 2 críticos, 3 altos, 3 medios, 3 bajos. Ver `addons/leulit_comercial/PLAN_REVISION.md`.
- [x] leulit_compras — 2026-09-10: módulo mínimo (solo un menú), 1 alto (a confirmar), resto medio/bajo. Ver `addons/leulit_compras/PLAN_REVISION.md`.
- [x] leulit_crm_team — 2026-09-10: 2 críticos, 3 altos, 2 medios, 0 bajos. Ver `addons/leulit_crm_team/PLAN_REVISION.md`.
- [x] leulit_encuestas — 2026-09-10: 1 crítico, 4 altos, 4 medios, 5 bajos. Ver `addons/leulit_encuestas/PLAN_REVISION.md`.
- [x] leulit_escuela — 2026-09-10: 3 críticos, 5 altos, 8 medios, 7 bajos. Ver `addons/leulit_escuela/PLAN_REVISION.md`.
- [x] leulit_esignature — 2026-09-10: 3 críticos, 9 altos, 8 medios, 4 bajos — firma electrónica rota (OTP comparado con sí mismo, endpoint `hacksignature`). Ver `addons/leulit_esignature/PLAN_REVISION.md`.
- [x] leulit_groups_manager — 2026-09-10: 0 críticos, 4 altos, 4 medios, 4 bajos. Ver `addons/leulit_groups_manager/PLAN_REVISION.md`.
- [x] leulit_hide_menus — 2026-09-10: 1 crítico, 1 alto, 1 medio, 2 bajos. Ver `addons/leulit_hide_menus/PLAN_REVISION.md`.
- [x] leulit_ia — 2026-09-10: 1 crítico, 4 altos, 5 medios, 4 bajos. Sin referencias Enterprise. Revisión del antiguo asistente de chat; el módulo se sustituyó el 2026-09-21 por la búsqueda universal (antes `leulit_ai`), así que `PLAN_REVISION.md` ya no existe (recuperable en git).
- [x] leulit_meteo — 2026-09-10: 1 crítico ⚠️ API KEY DE AEMET EXPUESTA EN CLARO en `aemet-api-key.md` (commit 6c01861d) — ROTAR YA —, 4 altos, 7 medios, 4 bajos. Ver `addons/leulit_meteo/PLAN_REVISION.md`.
- [x] leulit_nda — 2026-09-10: 0 críticos, 5 altos, 5 medios, 6 bajos. Ver `addons/leulit_nda/PLAN_REVISION.md`.
- [x] leulit_operaciones — 2026-09-10: 14 críticos, 19 altos, ~24 medios, ~20 bajos. Ver `addons/leulit_operaciones/PLAN_REVISION.md`.
- [x] leulit_parte_145 — 2026-09-10: 4 críticos, 4 altos, 7 medios, 3 bajos. Ver `addons/leulit_parte_145/PLAN_REVISION.md`.
- [x] leulit_parte_privado — 2026-09-10: 1 crítico, 1 alto, 3 medios, 3 bajos. Confirmado 100% aditivo (no toca workflow de leulit.vuelo). Ver `addons/leulit_parte_privado/PLAN_REVISION.md`.
- [x] leulit_partis — 2026-09-10: 6 críticos, 6 altos, 6 medios, 4 bajos — 4 subsistemas SGSI no funcionales. Ver `addons/leulit_partis/PLAN_REVISION.md`.
- [x] leulit_planificacion — 2026-09-10: 4 críticos, 6 altos, ~10 medios, ~8 bajos. Ver `addons/leulit_planificacion/PLAN_REVISION.md`.
- [x] leulit_seguridad — 2026-09-10: 3 críticos, 4 altos, 6 medios, 3 bajos. Ver `addons/leulit_seguridad/PLAN_REVISION.md`.
- [x] leulit_taller — 2026-09-10: 5 críticos, 8 altos, 11 medios, 4 bajos. Ver `addons/leulit_taller/PLAN_REVISION.md`.
- [x] leulit_tarea — 2026-09-10: 3 críticos, 4 altos, 3 medios, 1 bajo. Ver `addons/leulit_tarea/PLAN_REVISION.md`.
- [x] leulit_trabajador_externo — 2026-09-10: 2 críticos, 0 altos, 3 medios, 4 bajos — probablemente no funcional (sin `ir.model.access`). Ver `addons/leulit_trabajador_externo/PLAN_REVISION.md`.
- [x] leulit_user_impersonate — 2026-09-10: 3 críticos, 6 altos, 7 medios, 4 bajos — suplantación sin log real ni expiración. Ver `addons/leulit_user_impersonate/PLAN_REVISION.md`.
- [x] leulit_ventas — 2026-09-10: módulo mínimo (solo un menú), 1 alto (a confirmar), resto medio/bajo. Ver `addons/leulit_ventas/PLAN_REVISION.md`.
- [x] maintenance_equipment_changes — 2026-09-10: 2 críticos, 4 altos, 7 medios, 5 bajos. Ver `addons/maintenance_equipment_changes/PLAN_REVISION.md`.

## Plantilla de prompt para revisar un módulo

Sustituir `[MÓDULO]` por el nombre del addon y pegar en
Claude Code.

```
<context>
Proyecto Odoo 17.0 Community. Addon a revisar ubicado en `addons/[MÓDULO]/`. No hay entorno Odoo local disponible: toda la verificación es por lectura de código, no por ejecución.
</context>

<task>
Actúa como ingeniero senior de Odoo especializado en Python/ORM. Revisa TODO el código del addon `addons/[MÓDULO]/` (modelos, vistas XML, seguridad, controladores, wizards, cron jobs, reports) y produce un informe de hallazgos accionable, ordenado por severidad.

Cubre específicamente:
1. **Errores/bugs**.
2. **Seguridad**.
3. **Rendimiento**.
4. **Mantenibilidad/mejoras**

Para cada hallazgo indica: fichero:línea, severidad (crítico/alto/medio/bajo), qué falla concretamente (con el escenario de entrada que lo dispara), y la corrección propuesta.
</task>

<constraints>
- Alcance: SOLO ficheros dentro de `addons/[MÓDULO]/`. Si detectas que el bug depende de un campo/método definido en OTRO módulo, señálalo pero no lo "arregles" fuera del alcance sin preguntar primero.
- Es una revisión, no una implementación: NO edites ningún fichero de código del módulo. Si quieres proponer un fix, muéstralo como diff o snippet dentro del informe. La única escritura permitida es el documento de salida indicado en `<output_format>`.
- No puedes ejecutar el módulo ni una BBDD real: toda afirmación de "esto falla" debe justificarse leyendo el código (imports, herencias, `_inherit`, `depends` del manifest), no asumida.
- No fabriques APIs de Odoo que no existan en 17.0; si tienes dudas sobre un método de la ORM, dilo explícitamente en vez de inventarlo.
- Si el hallazgo requiere tocar un campo/AVD que aparece en varios sitios del repo (patrón ya visto en este proyecto), haz un grep exhaustivo de todos los sitios afectados antes de darlo por cerrado — no reportes solo el primero que encuentres.
- Ante cualquier duda, ambigüedad o decisión que no se pueda resolver solo leyendo el código (p.ej. si un comportamiento raro es un bug o una regla de negocio intencional, o cómo priorizar un fix con trade-offs), NO asumas ni decidas por tu cuenta: pregúntame explícitamente antes de cerrar ese hallazgo. Si hay varias decisiones de este tipo acumuladas, usa la skill `grill-me` (o una interrogación equivalente) para repasarlas conmigo una a una en vez de enterrarlas en el documento.
</constraints>

<output_format>
El entregable es un documento Markdown escrito en `addons/[MÓDULO]/PLAN_REVISION.md` (crear el fichero si no existe, sobrescribir si ya existe). No lo muestres solo en el chat: el fichero es el resultado real. Estructura, en este orden:
1. Resumen ejecutivo (máx. 5 líneas: cuántos hallazgos por severidad)
2. Tabla de hallazgos: | Severidad | Fichero:línea | Problema | Escenario que lo dispara | Fix propuesto |
3. Hallazgos críticos/altos desarrollados uno a uno con snippet de código actual + fix propuesto
4. Plan de acción: lista ordenada y priorizada de los cambios a aplicar en este módulo, cada uno con su severidad y el fichero afectado, para poder ejecutarla en una sesión posterior
5. Sección aparte "Dudas/no verificable sin entorno" si algo requeriría ejecución real para confirmarse
</output_format>
```
