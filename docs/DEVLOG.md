# DEVLOG

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
