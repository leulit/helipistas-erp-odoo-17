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
