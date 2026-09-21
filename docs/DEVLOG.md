# DEVLOG

## 2026-09-21 — leulit_almacen: estantería y caja editables (desplegables encadenados) al recepcionar

**Contexto:** las columnas caja/estantería del diálogo de líneas de S/N-lote (commit `8a7150fa`)
eran solo lectura. Se pidió poder elegirlas, sin errores de usuario.

**Decisión:** primero estantería, luego caja filtrada por esa estantería. Solo se eligen
estanterías y cajas existentes (`no_create`); no se mueven cajas desde aquí.
- `stock.move.line.estanteria_destino_id` (stored, dominio `_domain_estanteria()`), sustituye a
  los computados `caja_actual_id`/`estanteria_actual_id`.
- La caja es el `result_package_id` nativo, ahora visible, con dominio
  `[('estanteria_id','=',estanteria_destino_id)]` y readonly hasta elegir estantería.
- `onchange(lot_name)`: si el S/N ya existe, propone su caja/estantería actuales; cambiar la
  estantería vacía la caja si no encaja; aviso (no bloqueo) si la pieza ya existe en otro sitio.
- `_check_caja_en_estanteria` refuerza la coherencia en servidor.
- `_action_done`: con caja, propagan los hooks de `stock.quant`; sin caja se escribe
  `stock.lot.estanteria_id` (salvo que el lote ya esté en una caja: manda la caja).

**Consecuencias:** campo nuevo almacenado → `./upd_module.sh leulit_almacen prod --stop`.
Sin verificar en Odoo (no hay instancia local).

## 2026-09-18 — leulit_almacen: caja/estantería actuales al recepcionar (detección de duplicados)

**Contexto:** en el diálogo de líneas de detalle (S/N, Lote, Referencia Origen, Revisión,
Fecha Caducidad) que se abre al recepcionar un producto trazado por lote/serie
(`view_stock_move_line_operation_tree_leulit`, hereda `stock.view_stock_move_line_operation_tree`),
no había forma de saber si el S/N/lote que se está tecleando ya existía como pieza en
almacén, con el riesgo de recepcionar duplicados sin darse cuenta.

**Decisión:** dos campos computados no-store en `stock.move.line`
(`addons/leulit_almacen/models/stock_move_line.py`), `caja_actual_id` y
`estanteria_actual_id`, calculados por `_compute_pieza_existente` (depende de
`lot_name`, `product_id`, `company_id`): busca un `stock.lot` existente con ese
`name`+`product_id`+`company_id` y, si lo encuentra, copia su `caja_id`/`estanteria_id`
actuales (campos ya existentes en `stock.lot`, mantenidos por el propio módulo). Vacíos
si la pieza es nueva. Añadidos como columnas de solo lectura en la misma vista, justo
después de Fecha Caducidad.

Se descartó reutilizar `result_package_id` (caja destino del propio movimiento): en una
recepción nueva ese campo está vacío por definición, no sirve para detectar que la pieza
ya está en otro sitio del almacén.

**Consecuencias:** ningún cambio de esquema (campos `store=False`, sin `ALTER TABLE`),
así que la actualización del módulo no requirió `--stop`. Verificado end-to-end en
producción vía MCP odoo (solo lectura): `odoo_fields_get` confirma los campos nuevos en
`stock.move.line`, y sobre una línea real (`stock.move.line` id 27273, pieza SAFRAN)
`caja_actual_id`/`estanteria_actual_id` devuelven la misma caja/estantería que su
`stock.lot` correspondiente. Desplegado con `./upd_module.sh leulit_almacen prod`.

Commit: `8a7150fa`.

## 2026-09-21 — leulit_tarea: "Tareas por semana y estado" pasa de pivot a tabla custom

**Contexto:** el pivot sobre `project.task` agrupaba por `date_last_stage_update` (semana) y
`stage_id`, de modo que cada tarea contaba una sola vez, en la semana de su último cambio de
etapa. No puede dar la foto semanal ("cuántas estaban Pendientes al cierre de la semana X"),
que es lo que se quiere ver.

**Decisión:** se elimina el pivot (vista, acción, JS/SCSS y los filtros `filter_emilio_pau` y
`filter_last_12_weeks`, huérfanos) y se sustituye por un `TransientModel`
`leulit.tarea.semana.estado` (`models/tarea_semana_estado.py`). El menú abre una
`ir.actions.server` (`leulit_20260921_1101_action`, id nuevo) que llama a `abrir_tabla()`:
borra las filas previas del usuario, recalcula y devuelve un tree sin create/edit/delete.
Criterios:
- Últimas 12 semanas ISO (la actual incluida); corte = domingo 23:59:59, o `now` en la actual.
- Usuarios fijos 11 (Emilio) y 14 (Pau): ambos -> "Ambos"; solo 11 -> Emilio; solo 14 -> Pau;
  terceros ignorados. Asignados actuales, una vez por tarea y semana. Incluye archivadas y
  excluye `project_borrador`; solo tareas creadas antes del corte.
- Etapa al corte reconstruida desde `mail.tracking.value` de `stage_id` (una sola búsqueda);
  sin trackings, `stage_id` actual. Pendiente/En proceso/Pospuesta = foto al corte;
  Realizada = etapa "hecha" al corte y entrada en ella dentro de esa semana. Mapeo por nombre
  en `ETAPA_A_COLUMNA`; "N/A" y otros se ignoran.
- Siempre 12 semanas x 3 personas (aunque sea 0).
- Fechas en UTC (naive) tal como las guarda Odoo; el corte de domingo no aplica huso horario.

**Consecuencias:** modelo nuevo -> `./upd_module.sh leulit_tarea prod --stop` (DDL). Los
transient se vacían solos (vacuum). El histórico depende de que existan trackings de etapa:
tareas movidas antes de que se rastreara `stage_id` darían fotos aproximadas. Test en
`addons/leulit_tarea/tests/`. Sin ejecutar (no hay Odoo local).
