# Revisión de código — `addons/leulit_operaciones`

Revisión estática (sin entorno Odoo ejecutable) de todo el addon: modelos, vistas XML, seguridad, wizards, reports. Odoo 17.0 Community. Depende de (`__manifest__.py`): `leulit`, `leulit_parte_145`, `leulit_tarea`, `leulit_meteo`.

## 1. Resumen ejecutivo

**14 críticos, 19 altos, ~24 medios, ~20 bajos.** Los críticos más graves son de dos tipos: (a) **seguridad de vuelo real** — un bug de una línea en `initChainToCerrado()` desactiva la validación de combustible al cerrar cualquier vuelo, y un fichero completo (`leulit_vuelo_scripts.py`) permite a cualquier usuario cerrar/firmar/borrar vuelos por RPC con un OTP hardcodeado; (b) **integridad de datos y ACL** — el modelo `leulit.vuelo` es borrable por cualquier empleado (único `ir.model.access` del modelo, sin `ir.rule`, sin `unlink()`, vistas sin `delete="0"`), y varios cálculos de horas de vuelo/piloto (`leulit_piloto.py`, `technical_log_report.py`) lanzan `TypeError`/`AttributeError` garantizados en cuanto se leen. Dos informes QWeb (`registro_consumosaeronave_report.xml`, `registro_vuelo_aeronaves.xml`) están rotos al 100% por un `t-call` a un template inexistente.

## 2. Tabla de hallazgos

| Severidad | Fichero:línea | Problema | Escenario que lo dispara | Fix propuesto |
|---|---|---|---|---|
| Crítico | `security.xml:4-12` + `models/leulit_vuelo.py` (sin `unlink()`) + `menu.xml:18-31` + `views/leulit_vuelo.xml:1590,1615,9` | `perm_unlink=1` para `leulit.RBase` sobre `leulit.vuelo` (único ACL del modelo, sin `ir.rule`); menús "Partes de vuelo"/"Partes de vuelo Futuro" sin `groups`; vistas tree/form/kanban sin `delete="0"` | Cualquier empleado abre "Partes de vuelo" y borra un vuelo `cerrado` desde el icono de papelera | Añadir `unlink()` en el modelo que bloquee `estado in ('cerrado','cancelado')` salvo grupo explícito; añadir `delete="0"` en las vistas; revisar si `perm_unlink=1` a `RBase` sigue siendo la intención |
| Crítico | `models/leulit_vuelo.py:142-154` | `chain7` se reasigna antes de encadenar: `ComprobacionDatosCombustibleHandler` nunca se ejecuta al pasar a `cerrado` | Cerrar cualquier vuelo — la validación de combustible mínimo/relación fuel salida-llegada se salta siempre | Usar variables distintas para cada handler y encadenarlos todos |
| Crítico | `models/leulit_vuelo_scripts.py:16-73` | OTP hardcodeado (`'654321'`/`'123456'`), `write()` directo del estado sin pasar por las cadenas de validación, impersonación vía `sudo().with_user()`; `perm_create/write=1` para `RBase` | Cualquier usuario autenticado invoca `firmar_cerrar_vuelo(idvuelo)`/`firmar_postvuelo_vuelo(idvuelo)` por RPC sobre cualquier vuelo, saltándose descanso de tripulación, checklist, combustible, W&B | Eliminar del build de producción, o restringir a grupo IT y reemplazar `write()` directo por `wkf_act_cerrado()`/`wkf_act_postvuelo()` |
| Crítico | `models/leulit_vuelo_scripts.py:127-148` | `set_unlink_vuelo()` borra en cascada todos los vuelos + W&B + performance de `piloto_id=17` hardcodeado, invocable por cualquier `RBase` | Cualquier usuario invoca `set_unlink_vuelo()` por RPC | Eliminar o restringir a IT; nunca en producción |
| Crítico | `models/leulit_weight_and_balance.py` (campos `valid_*cg`) | Los booleanos de validez del CG son `fields.Boolean()` normales, escribibles por cualquiera; `determineIfPointLiesWithinPolygon()` no tiene invocadores — sin revalidación server-side | Escribir por RPC `valid_takeoff_longcg=True` sobre un vuelo con CG realmente fuera de envolvente | Hacerlos `compute=..., store=True` invocando `determineIfPointLiesWithinPolygon()`, no campos editables libremente |
| Crítico | `models/leulit_vuelo.py` `_calc_tiempo_vuelo_max` (~1951-1958) | `item.fuelsalida / item.consumomedio_vuelo` sin guardar contra 0 | Vuelo nuevo antes de seleccionar helicóptero (`consumomedio_vuelo=0`) | `if item.consumomedio_vuelo else 0` |
| Crítico | `models/leulit_vuelo.py` `_is_last_30_days` (~2174-2183) | `datetime.strptime(item.fechavuelo, "%Y-%m-%d")` sobre un `fields.Date` (ya es `date`, no string) → `TypeError`; además `return True/False` en vez de asignar `item.is_last_30_days` | Cualquier cómputo/lectura de este campo | Reescribir con `hoy - item.fechavuelo` y asignación `item.is_last_30_days = ...` |
| Crítico | `tests/test_weigh_and_balance.py:8-11` | `self.employee.create(...)` — `self.employee` no existe | Ejecutar el test suite del módulo | `self.wandb.create(...)` (el modelo correcto ya está en `self.wandb`) |
| Crítico | `models/leulit_piloto.py:133,140,147,154,161,171` vs `384,392,408,440,448` | `item._calc_horas_totales_vuelo(item.id)` etc. pasan un argumento posicional a métodos definidos como `def _calc_xxx(self, ):` (sin parámetros) | Leer cualquiera de `hv`, `hv_pm`, `hv_inst`, `hv_dm`, `hv_night`, `hv_ifr` en un piloto | Quitar el argumento en las 6 llamadas: `item._calc_horas_totales_vuelo()` |
| Crítico | `models/technical_log_report.py:76` | `self.pool['leulit.vuelo']` — API eliminada en Odoo 17 | Computar/leer `vuelos_ng` | `self.env['leulit.vuelo']` |
| Alto→Medio | `models/leulit_meteo_limits.py:13` | Modelo `leulit.meteo_limits` sin `ir.model.access`, sin vista, sin menú, sin ninguna referencia en el repo | Cualquier código que intente usar el modelo (hoy: ninguno) obtendría `AccessError` | Añadir el ACL en `security.xml` y una vista/menú, o eliminar el modelo si no está en desarrollo activo (preguntar al usuario) |
| Crítico | `views/registro_consumosaeronave_report.xml:96` | `t-call="leulit.Registro_consumosaeronave_css"` — template inexistente (el real es `leulit_operaciones.registro_consumosaeronave_css`, minúscula) | Generar el informe "Consumos por vuelo" | Corregir el `t-call` al id real |
| Crítico | `views/registro_vuelo_aeronaves.xml:96` | Mismo bug: `t-call="leulit.Registro_vuelo_aeronaves_css"` inexistente | Generar el informe "Registro vuelos aeronave" | Corregir el `t-call` al id real |
| Crítico (alta confianza, no ejecutado) | `views/hr_expense.xml:15-19` | Dos `<xpath expr="//field[@name='price_unit']" position="replace">` consecutivos sobre el mismo nodo — el primero lo borra, el segundo ya no lo encuentra | Cargar/actualizar el módulo (`./upd_module.sh leulit_operaciones dev`) | Eliminar el primer `xpath` redundante, dejar solo el segundo |
| Alto | `models/leulit_vuelo.py:85-118` | `checkValidCreateWriteData()` (verifica solapamiento horario piloto/helicóptero) no tiene ningún invocador en todo el repo | `write()`/`create()` directo (form en `prevuelo`, import, RPC) no dispara ninguna comprobación de solapamiento | Invocar desde `write()`/`create()`, o confirmar con el usuario si la validación vive en otro sitio no localizado |
| Alto | `models/leulit_vuelo.py:2103-2107` `wizardSetPrevuelo` | Fuerza `estado='prevuelo'` sin comprobar el estado previo | Invocación (origen no localizado en este addon) sobre un vuelo `cerrado`/`postvuelo` | Comprobar estado antes de revertir, o confirmar que es intencional |
| Alto | `models/leulit_vuelo.py:1079-1087` `obtener_peso()` | Bug multi-registro (solo sobrevive el último `item`), `UnboundLocalError` si `self` vacío, SQL sin `LIMIT`/parametrización | Llamar sobre recordset vacío o multi-registro | `self.ensure_one()`, `fetchone()`, SQL parametrizado con `%s` |
| Alto | `models/leulit_vuelo.py` `onchange_helicoptero` (~1556-1601) | `item.write(...)` y `obj_perf.unlink()` dentro de un `@api.onchange` — persiste en BD antes de guardar el formulario | Cambiar el helicóptero en el form y luego cancelar sin guardar | Mover el side-effect a `write()`/botón explícito, dejar el onchange puro |
| Alto | `models/leulit_vuelo.py` (usa `isHelicopterBlocked()`) | Método solo definido en `leulit_seguridad`, que NO es dependencia declarada ni transitiva de `leulit_operaciones` | Instalar `leulit_operaciones` sin `leulit_seguridad` presente → `AttributeError` al cerrar/postvuelear | Añadir `leulit_seguridad` a `depends`, o confirmar con el usuario que siempre está instalado |
| Alto | `vuelo_chain_cerrado.py:89-127` vs `models/leulit_vuelo.py:859-894` | Lógica de descanso de tripulación duplicada y divergente: falta un `else`/corte de bucle, y el umbral usa `>` en un sitio y `>=` en otro | Un vuelo justo en el límite de descanso mínimo se trata distinto según cuál copia corre | Eliminar `checkDescansoPiloto` (dead code) y dejar una sola implementación con el umbral correcto (confirmar cuál es el correcto con el usuario) |
| Alto | `models/leulit_weight_and_balance.py` `recalculate_weight_and_balance()` (~398-408) | `inicio = i*numblocks` en vez de `i*100` — paginación rota, salta bloques enteros de registros | Recalcular W&B en lote con más de un bloque de 100 registros | Bucle `while` con `offset` incremental de 100 hasta `search()` vacío |
| Alto | `models/leulit_performance.py:16-25` `create()` | `self._cr.execute(sql)` sin `fetchone()`; el bloque "actualizar si existe" nunca se ejecuta → duplica `leulit.performance` por vuelo; además interpola `vals['vuelo']` sin parametrizar | `create()` invocado más de una vez para el mismo `vuelo_id` (RPC/import) | Reescribir con `search([('vuelo','=',...)], limit=1)` + `write()`, SQL parametrizado si se mantiene |
| Alto | `models/hr_expense.py:40-41` | `.sudo()` lee `plus_festivo_nacional` (protegido con `groups="hr.group_hr_user"`) y lo copia a `price_unit`/`total_amount_currency`, visibles en el form de gasto | Si el form permite elegir `employee_id` de otra persona, un usuario sin `hr.group_hr_user` vería el plus salarial de un compañero | Ver "Dudas" — no proponer `ir.rule` sobre `hr.employee` (gotcha documentado del proyecto) |
| Alto | `models/sale_order.py:50-59` `search_is_flight_part()` | Solo maneja `operator=='=' and value==True`; cualquier otro caso devuelve `[('id','in',[])]` (vacío) en vez de la negación correcta | Filtrar `flag_flight_part = False` en cualquier vista/búsqueda | Implementar explícitamente la rama negativa |
| Alto | `views/google_places_template.xml:6` | API key de Google Maps hardcodeada en claro (`AIzaSyCh4m4h_SZyhCxLxZ_3jmmApRLI2hBndmE`), versionada en git | Cualquiera con acceso al repo ve la key | Rotar y mover a `ir.config_parameter`, igual que las keys de OpenAIP/CheckWX |
| Alto | `models/leulit_piloto.py:315-333` | IDs de grupo hardcodeados (`104`, `108`) en `_is_piloto_helipistas`/`_search_piloto_helipistas` | Cualquier entorno nuevo o tras reinstalación donde esos IDs de fila no coincidan con los grupos esperados | Usar `self.env.ref('leulit.<xmlid_grupo>').id` |
| Alto | `models/leulit_vuelo_wizard_report.py` `create_report()` (~línea 56) | `delta = to_date - from_date` sin comprobar que ambas fechas estén informadas | Generar el informe sin rellenar una de las dos fechas | `if not from_date or not to_date: raise UserError(...)` antes de restar |
| Alto | `menu.xml:294-307` + `views/leulit_hist_weight_and_balance.xml` (tree/form) | "Weight And Balance" (histórico) sin `groups`, vistas sin `create=/edit=/delete="0"`, sin `mail.thread` | Cualquier usuario con acceso al menú CAMO/Taller crea/edita/borra el histórico de W&B sin dejar rastro | Restringir ACL/vista para este modelo histórico |
| Alto | `report/report_format_27.xml` (21 líneas: 156,175,181,...,289) | `'data:image/png ;base64,%s'` — espacio extra antes de `;base64` en el data-URI | Generar el informe de conformidad Part-145 (firmas de inspección semanal EC120) | Quitar el espacio en las 21 ocurrencias |
| Alto | `report/ficha_vuelo_report.xml:1057-1058,1075-1076` + `views/ficha_vuelo_report_4_0_1.xml:915-916,933-934` | `style="background-color: ${color}"` — sintaxis Mako no evaluada en QWeb, sin `t-set="color"` en el fichero | Imprimir cualquier ficha de vuelo — el resaltado de CG fuera de envolvente no se pinta | Calcular el color en Python y aplicarlo con `t-attf-style`/`t-att-style` |
| Alto | `report/ficha_vuelo_report.xml:1177` + `views/ficha_vuelo_report_4_0_1.xml:999` | `t-raw` sobre `meteo` (`fields.Text` libre, editable por el piloto, sin sanitizar) | El piloto escribe `<` o `>` en el campo meteo de un parte de vuelo | Cambiar a `t-esc`/`t-out` con `white-space: pre-wrap` |
| Alto | `views/registro_consumosaeronave_report.xml:109` + `views/registro_vuelo_aeronaves.xml:113` | `docs[0].helicoptero_id.name` sin comprobar que `docs` no esté vacío | Generar el informe con un rango de fechas/helicóptero sin vuelos cerrados | Guardar contra lista vacía antes de generar el informe (en el wizard `leulit_vuelo_wizard_report.py`) |
| Alto | `models/leulit_helipuerto.py:402` `action_exportar_mapa_kmz` | `if record.lat is False or record.long is False:` — comparación de identidad sobre un `Float` (vacío = `0.0`, nunca `False`) | Exportar KMZ con helipuertos sin coordenadas | `if not record.lat and not record.long:` |
| Medio | `models/leulit_16_bravo.py:20-30` | `create()`/`write()` devuelven `False` en vez de lanzar excepción ante entrada inválida | Cualquier caller que confíe en el contrato ORM estándar | `raise ValidationError(...)` en vez de `res = False` |
| Medio | `models/leulit_16_bravo.py` (~57-59) | `dp.get_precision('leulit_2d_actividad_dp')` — nombre no localizado en `leulit/precision.xml`, posible typo | Cálculo con la precisión decimal equivocada | Confirmar el nombre real (ver Dudas) |
| Medio | `models/leulit_hist_weight_and_balance.py:17-21` | `unlink()` protegido con `UserError`, `write()` equivalente comentado | Editar un histórico usado como referencia justo antes de un cálculo nuevo | Ver "Dudas" — decidir si reactivar la protección de `write()` |
| Medio | `models/leulit_helipuerto.py:33-34` `create()` | `if vals.get('elevacion') == 0: raise UserError(...)` bloquea un helipuerto legítimo a nivel del mar; solo se valida en `create()`, no en `write()` | Crear un helipuerto con elevación real 0 ft | Ver "Dudas" — confirmar si 0 debe bloquearse |
| Medio | `models/leulit_rel_planoperacional_aerovia.py:52-67` `fill_altitudprevista`/`run_fill_altitudprevista` | Recalcula TODA la tabla en un hilo en background, sin `self.ids`, sin `try/except`, con `commit()` por fila | Pulsar el botón asociado (alcance no confirmado desde este addon) | Ver "Dudas" — filtrar por `self.ids` si el botón es por-registro; envolver en `try/except` con log |
| Medio | `models/leulit_vuelo.py` `_get_combustible_remanente` (~1345-1360) | `item.write(...)` dentro de un método `@api.depends` | Leer el campo dispara una escritura inesperada / posibles recomputes en cascada | Mover el side-effect fuera del compute |
| Medio | `models/leulit_vuelo.py` `_utc_horallegadaprevista` (~2020-2026) | Guarda `item.lugarsalida` pero calcula con `item.lugarllegada.tz` | Vuelo con `lugarllegada` vacío pero `lugarsalida` informado | Corregir la guarda a `item.lugarllegada` |
| Medio | `models/res_partner.py:17-26` `getPiloto`/`getOperador` | `search(...)` sin `limit=1`, solo usa el primer resultado | Cualquier llamada — coste innecesario si hubiera más de un match | Añadir `limit=1` |
| Medio | `models/leulit_ruta_aerovia.py:47-64` `_search_name` | Ignora `operator`, siempre hace "contiene"; escanea toda la tabla en Python | Filtro avanzado con `operator='!='` sobre el campo `name` | Manejar `operator` explícitamente o delegar en domain nativo |
| Medio | `views/leulit_weight_and_balance.xml:653-670` vs `689-706` (y `671-688` vs `707-724`) | Filas "Cargo load"/"Cargo hook" duplicadas con condiciones `invisible` que se solapan para la matrícula real EC-HIL | Abrir W&B de un helicóptero EC-HIL | Fusionar en una sola fila con condición combinada correctamente |
| Medio | `views/leulit_informe_seguros.xml:10` | Tree de `leulit.seguro_report` (vista SQL `_auto=False`) con `create="false" edit="false"` pero sin `delete="false"` | Pulsar borrar en la lista → error SQL poco claro | Añadir `delete="false"` |
| Medio | `views/leulit_operaciones_performance.xml:17` | Tree `editable="bottom"` sin `create=`/`delete="0"`; menú sin `groups` propio (hereda `ROperaciones_piloto`) | Cualquier piloto edita/borra el catálogo de referencia de performance | Restringir grupo o vista |
| Medio | `models/leulit_helicoptero.py:16,24` | `_get_sling_cycles` sin `@api.depends`; `_calc_arlandings_helicoptero` con `@api.depends('arlandingstart')` incompleto (falta dependencia de `vuelo_ids`) | El valor no se invalida al crear/cerrar un vuelo relacionado | Añadir las dependencias correctas |
| Medio | `models/hr_expense.py:31` | `self.date.month` sin comprobar que `self.date` esté informado | Onchange con `date` vacío | `if self.date and 5 <= self.date.month <= 9:` |
| Bajo→Medio | `views/registro_ciclos_report.xml` | No está en `__manifest__.py` `data` (huérfano); su template QWeb está enteramente comentado (sintaxis Mako antigua) | N/A — nunca se carga | Eliminar el fichero o completarlo y añadirlo al manifest |
| Bajo | `models/leulit_piloto.py:51-53` `copiloto()` | Siempre devuelve `False`, ignora sus parámetros | Cualquier llamada | Ver "Dudas" — ¿stub pendiente? |
| Bajo | `models/leulit_piloto.py:202,210,218` / `267,275` | `_start_hv_inst` definido 3 veces, `_start_hv_ifr` 2 veces (idénticos) | N/A, solo mantenibilidad | Eliminar duplicados |
| Bajo | `models/leulit_vuelo.py:797` (etiqueta) | `<fields name="nv_date" invisible="1"/>` — tag XML inválido, Odoo lo ignora silenciosamente | El campo `nv_date` no se comporta como se pretendía en el form | `<field name="nv_date" invisible="1"/>` |
| Bajo | `static/src/xml/parte_vuelo_buttons.xml` | Mecanismo legacy `t-extend`/`t-jquery` (pre-OWL), contenido íntegramente comentado | N/A hoy (inerte) | Ver "Dudas" — limpiar si es descarte confirmado |
| Bajo | Varios reports (`ficha_vuelo_report_4_0_1.xml:65`, `registro_consumosaeronave_report.xml:101`, `registro_vuelo_aeronaves.xml:101`) | URL S3 hardcodeada al logo en vez de `res.company.logo_hlp` | N/A, solo mantenibilidad | Usar el logo dinámico de compañía |
| Bajo | `models/leulit_vuelo.py` (~1845) `getNotamInfo` | API key de ICAO hardcodeada en claro | N/A | Rotar y mover a config, junto con la key de Google Maps |

*(Tabla no exhaustiva de hallazgos bajos — se han priorizado los que tienen impacto funcional real; el resto de notas de estilo/duplicación menor está detallado en los informes de los sub-agentes y se resume en el plan de acción.)*

## 3. Hallazgos críticos/altos desarrollados

### 3.1 [CRÍTICO] Borrado sin restricción de vuelos (`leulit.vuelo`)

`security.xml:4-12` es el **único** `ir.model.access` para `leulit.vuelo` en todo el repo custom (verificado por grep global de `model_id.*model_leulit_vuelo`):

```xml
<record id="leulit_20230906_1505_access_permission" model="ir.model.access">
    <field name="name">Vuelo Access</field>
    <field name="model_id" ref="model_leulit_vuelo"/>
    <field name="group_id" ref="leulit.RBase"/>
    <field name="perm_read" eval="1"/>
    <field name="perm_create" eval="1"/>
    <field name="perm_write" eval="1"/>
    <field name="perm_unlink" eval="1"/>
</record>
```

`leulit.RBase` es el grupo base que, según `CLAUDE.md` del proyecto, hereda prácticamente todo rol funcional vía `implied_ids`. No existe ningún `ir.rule` sobre `leulit.vuelo` en ningún módulo custom (verificado por grep). `models/leulit_vuelo.py` no define `unlink()`. Y las vistas que exponen el modelo sin restricción de rol (`menu.xml:18-31`, acciones `leulit_20250520_1024_action`/`leulit_20220818_1621_action`) usan tree/form/kanban (`views/leulit_vuelo.xml:1590,1615,9`) sin `delete="0"`.

Resultado: cualquier empleado con el menú "Vuelos" visible puede borrar un vuelo `cerrado` — un registro legal de la operación aérea — desde la lista, y lo mismo por RPC directo independientemente de la vista.

**Fix propuesto** (modelo, en `models/leulit_vuelo.py`):
```python
def unlink(self):
    for vuelo in self:
        if vuelo.estado in ('cerrado', 'cancelado') and not self.env.user.has_group('leulit.ROperaciones_responsable'):
            raise UserError(_("No se puede eliminar un vuelo %s.") % vuelo.estado)
    return super().unlink()
```
Y en vista, añadir `delete="0"` en los tres viewtypes citados como capa adicional (no sustituye el fix de modelo, que es la única protección real ante RPC).

### 3.2 [CRÍTICO] Validación de combustible desactivada al cerrar un vuelo

`models/leulit_vuelo.py:142-154`:
```python
def initChainToCerrado(self):
    chain1 = vuelo_chain_cerrado.ComprobacionPresupuestoHandler()
    chain2 = vuelo_chain_cerrado.ComprobacionChecksHandler()
    chain3 = vuelo_chain_cerrado.ComprobacionUsuarioPilotoHandler()
    chain4 = vuelo_chain_cerrado.ComprobacionHelicopteroHandler()
    chain5 = vuelo_chain_cerrado.ComprobacionDescansoHandler()
    chain6 = vuelo_chain_cerrado.ComprobacionDatosGeneralesHandler()
    chain7 = vuelo_chain_cerrado.ComprobacionDatosCombustibleHandler()
    chain7 = vuelo_chain_cerrado.ComprobacionParteEscuelaHandler()   # <-- pisa la instancia anterior
    chain8 = vuelo_chain_cerrado.UpdateProximoVueloHandler()

    chain1.set_next(chain2).set_next(chain3).set_next(chain4).set_next(chain5).set_next(chain6).set_next(chain7).set_next(chain8)
    return chain1
```
`ComprobacionDatosCombustibleHandler` (definido en `vuelo_chain_cerrado.py:292-307`, comprueba `fuelllegada`, relación `fuelsalida`/`combustibleminimo` y límites por tipo de helicóptero) queda fuera de la cadena — nunca se ejecuta al pasar un vuelo a `cerrado`. Solo se valida en `postvuelo` (`vuelo_chain_postvuelo.py`).

**Fix:**
```python
chain7 = vuelo_chain_cerrado.ComprobacionDatosCombustibleHandler()
chain7b = vuelo_chain_cerrado.ComprobacionParteEscuelaHandler()
chain8 = vuelo_chain_cerrado.UpdateProximoVueloHandler()
chain1.set_next(chain2).set_next(chain3).set_next(chain4).set_next(chain5).set_next(chain6).set_next(chain7).set_next(chain7b).set_next(chain8)
```

### 3.3 [CRÍTICO] `leulit_vuelo_scripts.py`: bypass total con OTP hardcodeado

```python
def run_firmar_cerrar_vuelo(self,idvuelo):
    ...
    for vuelo in vuelos:
        args={'otp':'654321','notp':'654321','modelo':'leulit.vuelo','idmodelo':vuelo.id}
        context['args']=args
        ...
        if user:
            env['leulit_signaturedoc'].with_context(context).sudo().with_user(user.id).checksignatureRef()
            new_cr.commit()
            vuelo.write({'estado':'cerrado'})
            new_cr.commit()
```
(`models/leulit_vuelo_scripts.py:16-73`). El OTP está fijo en el código (`'654321'`/`'123456'`), el estado se escribe directamente con `write()` sin pasar por `wkf_act_cerrado()`/`wkf_act_postvuelo()` (que son los que disparan `initChainToCerrado`/las cadenas de validación), y se impersona al piloto/supervisor con `sudo().with_user(user.id)`. `security.xml:166-174` da `perm_create`/`perm_write`/`perm_unlink=1` a `RBase` sobre `leulit.vuelo_scripts`, así que cualquier usuario autenticado puede invocar `firmar_cerrar_vuelo(idvuelo)` por RPC sobre cualquier vuelo del sistema.

En el mismo fichero, `set_unlink_vuelo()` (líneas 127-148) borra en cascada todos los vuelos + tipo_line + W&B + performance del piloto con `id=17` hardcodeado — también accesible sin restricción.

**Fix propuesto:** retirar este fichero del módulo instalable en producción (parece código de desarrollo/pruebas), o, si se necesita para algún proceso real, (a) restringir su ACL a un grupo IT, (b) sustituir el `write()` directo por las llamadas reales `wkf_act_cerrado()`/`wkf_act_postvuelo()` para no saltarse ninguna validación, (c) eliminar el OTP hardcodeado y el `id=17` hardcodeado.

### 3.4 [CRÍTICO] Cómputo de horas de vuelo del piloto: `TypeError` garantizado

`models/leulit_piloto.py:130-172`:
```python
@api.depends('start_hv')
def _calc_hv(self):
    for item in self:
        tiempo = item._calc_horas_totales_vuelo(item.id)   # <-- argumento posicional extra
        item.hv = tiempo
```
frente a la firma real del helper (línea 417):
```python
def _calc_horas_totales_vuelo(self, ):
    for item in self:
        ...
        return tiempo
```
`obj.metodo(arg)` contra `def metodo(self):` (sin parámetros) lanza siempre `TypeError: _calc_horas_totales_vuelo() takes 1 positional argument but 2 were given` — es semántica de Python, no una hipótesis de comportamiento de Odoo. El mismo patrón se repite en las 6 parejas: `_calc_hv`/`_calc_horas_totales_vuelo` (133↔417), `_calc_hv_pm`/`_calc_horas_piloto_almando` (140↔384), `_calc_hv_inst`/`_calc_horas_instructor` (147↔392), `_calc_hv_dm`/`_calc_horas_doblemando` (154↔408), `_calc_hv_night`/`_calc_horas_totales_nocturnas_vuelo` (161↔440), `_calc_hv_ifr`/`_calc_horas_totales_ifr_vuelo` (171↔448).

**Escenario de disparo:** cualquier lectura de `hv`, `hv_pm`, `hv_inst`, `hv_dm`, `hv_night` o `hv_ifr` (formulario/lista de piloto, informes de horas, 16 Bravo) dispara el error.

**Fix** (aplicar a las 6 líneas): `tiempo = item._calc_horas_totales_vuelo()` (sin argumento).

Nota adicional: los propios helpers (`_calc_horas_totales_vuelo` y hermanos) están escritos como `for item in self: ... return tiempo`, que retorna en la primera iteración — si alguna vez se invocan sobre un recordset multi-registro, solo se calcula el primero. Recomendado añadir `self.ensure_one()` al reescribirlos.

### 3.5 [CRÍTICO] `technical_log_report.py`: `self.pool` no existe en Odoo 17

```python
def _get_vuelos_ng(self):
    res = {}
    ng = 0.0
    for item in self:
        datos = self.pool['leulit.vuelo'].acumulados_motor_in_date(item.helicoptero_id.id, item.fecha)
        ng = datos['suma_ng']
        self.vuelos_ng = ng
```
(`models/technical_log_report.py:72-78`). `self.pool[...]` es el acceso a modelos de la API anterior a la v8; no existe en Odoo 17 → `AttributeError` garantizado al computar/leer `vuelos_ng`. **Fix:** `self.env['leulit.vuelo']`.

Además (mismo fichero, todos los `_get_*` de líneas 19-79): usan `self.<campo> = ...` en vez de `item.<campo> = ...` dentro de `for item in self:` — con un solo registro es invisible, pero en una vista de lista con varios `leulit.technical_log_report` a la vez, todos terminan con el valor del último `item` iterado. Y el campo `before_aritime` (línea 84, con typo) nunca recibe valor porque el compute escribe en `self.before_airtime` (sin typo, atributo Python distinto sin campo asociado) — bug combinado de nombre + `self`/`item`.

### 3.6 [CRÍTICO] Informes rotos por `t-call` a template inexistente

`views/registro_consumosaeronave_report.xml:96`:
```xml
<t t-call="leulit.Registro_consumosaeronave_css"/>
```
El template real definido en el mismo módulo es `leulit_operaciones.registro_consumosaeronave_css` (minúscula, namespace distinto) — no existe ningún `leulit.Registro_consumosaeronave_css` en el repo (grep global). El mismo bug exacto en `views/registro_vuelo_aeronaves.xml:96` (`t-call="leulit.Registro_vuelo_aeronaves_css"`). Ambos informes fallan al generarse.

**Fix:** corregir el `t-call` al id real del template definido en el propio fichero.

### 3.7 [CRÍTICO, no ejecutado — alta confianza] `hr_expense.xml`: xpath duplicado sobre el mismo nodo

```xml
<xpath expr="//field[@name='price_unit']" position="replace">
    <!-- ... contenido A ... -->
</xpath>
<xpath expr="//field[@name='price_unit']" position="replace">
    <!-- ... contenido B, con atributos nuevos ... -->
</xpath>
```
(`views/hr_expense.xml:15-19`). El primer `position="replace"` elimina el nodo `field[@name='price_unit']` del árbol de trabajo de la vista heredada; el segundo, que busca el mismo `expr`, ya no lo encuentra. Semánticamente esto debería producir el error típico de Odoo "Element ... cannot be located in parent view" al actualizar el módulo, rompiendo el formulario estándar de `hr.expense`. **Pendiente de confirmación en Docker de pruebas** (ver sección 5) — no se ha podido ejecutar `./upd_module.sh leulit_operaciones dev` desde este entorno.

**Fix:** eliminar el primer `<xpath>` (redundante) y dejar solo el segundo.

### 3.8 [ALTO] `checkValidCreateWriteData()` es código muerto

`models/leulit_vuelo.py:85-118` implementa la comprobación de solapamiento horario piloto/helicóptero descrita en `CLAUDE.md` del proyecto, pero no tiene **ningún** invocador en todo el repo (confirmado por grep recursivo, no solo en el addon). `leulit.vuelo` no sobrescribe `write()` en ningún módulo. El único punto donde se valida solapamiento son las cadenas `vuelo_chain_cerrado.py`/`vuelo_chain_postvuelo.py`, que solo corren al pulsar los botones de cambio de estado — un `write()` directo en `prevuelo` (formulario, import, RPC) no dispara ninguna comprobación. **Ver Dudas** — no está claro si esto es un descuido o si la validación se hace desde JS/otro módulo no cubierto por esta revisión.

## 4. Plan de acción priorizado

1. **[Crítico]** `models/leulit_vuelo.py:142-154` — arreglar la reasignación de `chain7` para que `ComprobacionDatosCombustibleHandler` se ejecute al cerrar un vuelo.
2. **[Crítico]** `models/leulit_vuelo_scripts.py` — decidir con el usuario si el fichero se retira del build de producción o se blinda (ACL restringido + eliminar OTP hardcodeado + usar `wkf_act_cerrado()`/`wkf_act_postvuelo()`).
3. **[Crítico]** `security.xml` + `models/leulit_vuelo.py` — decidir con el usuario el alcance del `unlink()` a implementar sobre `leulit.vuelo` (ver 3.1) y aplicar `delete="0"` en las vistas afectadas.
4. **[Crítico]** `models/leulit_piloto.py` — quitar el argumento posicional sobrante en las 6 llamadas de horas de vuelo (3.4).
5. **[Crítico]** `models/technical_log_report.py:76` — cambiar `self.pool` por `self.env`; y de paso corregir `self.`→`item.` en el resto de computes del fichero y el typo `before_aritime`/`before_airtime`.
6. **[Crítico]** `views/registro_consumosaeronave_report.xml:96` y `views/registro_vuelo_aeronaves.xml:96` — corregir el `t-call` a los templates reales.
7. **[Crítico]** `views/hr_expense.xml:15-19` — eliminar el primer `xpath` duplicado (verificar antes en Docker de pruebas).
8. **[Crítico]** `models/leulit_vuelo.py` (`_calc_tiempo_vuelo_max`, `_is_last_30_days`) — guardas contra división por cero y reescritura del compute de fecha.
9. **[Crítico]** `tests/test_weigh_and_balance.py:8-11` — corregir `self.employee`→`self.wandb` para que el test pueda ejecutarse (y ampliar cobertura, ver Dudas).
10. **[Crítico]** `models/leulit_weight_and_balance.py` — decidir con el usuario cómo revalidar `valid_*cg` en servidor (3.1 del resumen ejecutivo de los sub-agentes) — requiere diseño, no es un one-liner.
11. **[Alto]** `models/leulit_weight_and_balance.py` `recalculate_weight_and_balance()` — corregir la paginación (`i*100` en vez de `i*numblocks`).
12. **[Alto]** `models/leulit_performance.py:16-25` — reescribir `create()` para que la comprobación de duplicado funcione de verdad.
13. **[Alto]** `models/leulit_vuelo.py` `onchange_helicoptero` — sacar el `write()`/`unlink()` fuera del `@api.onchange`.
14. **[Alto]** `models/leulit_vuelo.py` (uso de `isHelicopterBlocked()`) — añadir `leulit_seguridad` a `depends` o confirmar con el usuario que siempre está presente.
15. **[Alto]** `views/google_places_template.xml:6` — rotar y externalizar la API key de Google Maps (agrupar con la rotación de keys ya pendiente en el proyecto).
16. **[Alto]** `report/report_format_27.xml` — quitar el espacio en las 21 ocurrencias de `data:image/png ;base64,`.
17. **[Alto]** `report/ficha_vuelo_report.xml` / `views/ficha_vuelo_report_4_0_1.xml` — arreglar el resaltado de color CG (`${color}`) y cambiar `t-raw` de `meteo` a `t-esc`.
18. **[Alto]** `models/hr_expense.py:40-41` — resolver junto con el usuario la exposición de `plus_festivo_nacional` vía `sudo()` (ver Dudas, no soluble solo con lectura de código).
19. **[Alto]** `models/sale_order.py:50-59` — implementar la rama negativa de `search_is_flight_part`.
20. **[Alto]** `models/leulit_piloto.py:315-333` — sustituir los IDs de grupo hardcodeados (104/108) por `env.ref(...)`.
21. **[Medio/Alto]** `models/leulit_vuelo.py:85-118` `checkValidCreateWriteData` — conectar la validación de solapamiento a `create()`/`write()` una vez resuelta la duda 5 (abajo).
22. **[Medio]** Resto de hallazgos medios de la tabla (huecos de `@api.depends`, N+1 en `search()` dentro de bucles, `_search_*` que ignoran `operator`, filas de vista W&B solapadas para EC-HIL, `leulit.meteo_limits` huérfano) — abordar en una segunda pasada tras cerrar los críticos/altos.
23. **[Bajo]** Limpieza de código muerto/duplicado señalada en la tabla (métodos `_start_hv_inst`/`_start_hv_ifr` repetidos, `registro_ciclos_report.xml` huérfano, `parte_vuelo_buttons.xml` legacy comentado, tag `<fields>` inválido en `leulit_vuelo.xml:797`).

## 5. Dudas / no verificable sin entorno

1. **`hr_expense.py`/`hr_employee.py`** — el campo `plus_festivo_nacional` está protegido con `groups="hr.group_hr_user"`, pero el onchange de `hr_expense.py:40-41` lo lee con `.sudo()` y lo copia a campos visibles del gasto. ¿El formulario de `hr.expense` permite a un usuario sin ese grupo seleccionar como `employee_id` a otra persona? Si es así, cualquiera podría ver el plus salarial de un compañero a través de este onchange. **No propongo restringir esto con un `ir.rule` sobre `hr.employee`** — el proyecto ya documentó que ese enfoque rompió calendarios/rosters (commit `e85e8f1a`, revertido) porque `hr.employee` se usa como modelo de referencia en todo el ERP. La decisión de cómo acotar este acceso concreto (limitar quién puede cambiar `employee_id` en el gasto, o quitar el `sudo()` aceptando que el campo quede vacío para no-HR) debe tomarla el usuario.
2. **`leulit_helipuerto.py:33-34`** — ¿es intencional que un helipuerto a nivel del mar (elevación 0 ft) no pueda crearse? Misma pregunta para `lat`/`long` exactamente 0.
3. **`leulit_rel_planoperacional_aerovia.py` `fill_altitudprevista`** — ¿es una utilidad de "recalcular todo" intencional, o el botón debería limitarse a `self.ids`?
4. **`leulit_piloto.py` `copiloto()`** — siempre devuelve `False` ignorando sus argumentos. ¿Stub pendiente de implementar o código muerto ya sustituido?
5. **`leulit_wizard_freelance_actividad_aerea.py`** — código de verificación por email con `random.randint`, sin expiración ni límite de intentos, en vez del OTP con `pyotp` que ya usa `leulit_esignature`. ¿Es una barrera de seguridad real o solo confirmación UX de que el usuario tiene acceso a su correo? Depende también de quién puede acceder al wizard (`security.xml` no cubre este caso con detalle).
6. **`leulit_ruta_aerovia.py` `xmlrpc_other_aerovias`** — el prefijo sugiere exposición externa vía XML-RPC. ¿Está efectivamente expuesto fuera de los controladores/ACL estándar?
7. **`res_users.py` `get_piloto_freelance`** — llama a `self.get_partner()`, no definido en este addon ni en el stock de Odoo 17 (`res.users` solo tiene el campo `partner_id`). Posiblemente viene de `leulit` u otro módulo dependiente — no verificable sin leer esos módulos.
8. **`leulit_vuelo.py` (uso de `isHelicopterBlocked()`)** — definido solo en `leulit_seguridad`, que no es dependencia declarada ni transitiva de `leulit_operaciones`. ¿Está `leulit_seguridad` garantizado siempre instalado junto a este addon en todos los entornos (dev/prod)?
9. **`leulit_vuelo.py`/`leulit_vuelo_scripts.py`** — uso de `self.env['leulit_signaturedoc']`, del módulo `leulit_esignature`, que tampoco está en `depends`. Misma pregunta que el punto anterior.
10. **`checkValidCreateWriteData()` y `check_exists_prev_flight_open`/`check_exists_flight_closed`** — sin invocadores en todo el repo. ¿Existía una vía de invocación (botón, JS) eliminada sin limpiar el código, o nunca llegaron a conectarse?
11. **`wizardSetPrevuelo`** — fuerza `estado='prevuelo'` sin comprobar el estado previo. ¿Intencional (reabrir un vuelo cerrado) o bug? No se ha podido confirmar desde qué vista/rol se invoca dentro de este addon.
12. **`leulit_hist_weight_and_balance.py`** — `write()` deliberadamente sin proteger (el `unlink()` sí lo está, y hay un `write()` comentado). ¿Decisión consciente o código de depuración olvidado?
13. **Menús que reutilizan una acción de `leulit_operaciones` sin `groups` propio dentro de menús CAMO/Taller** (`leulit_20201118_1547_menuitem`, `leulit_20201123_1036_menuitem`, `leulit_20220208_1052_menuitem`/`menuitem2`, `menu.xml:287-307`) — su protección real depende de los `groups` de los menús padre, definidos en `leulit_actividad`/`leulit_taller`/`leulit_parte_145` (fuera de alcance). Sin conocer esos `groups` no se puede cerrar si el riesgo de borrado sin restricción (3.1) se repite también ahí.
14. **`views/ficha_vuelo_report_4_0_1.xml`** — sigue activa en el manifest junto a la versión 4.4.0 vigente, con los bugs Mako sin migrar. ¿Se puede retirar, o hay partes de vuelo antiguos que necesitan reimprimirse con ese formato exacto?
15. **`static/src/xml/parte_vuelo_buttons.xml`** — mecanismo legacy `t-jquery`/`t-extend` con todo el contenido comentado. ¿Confirmáis que es un placeholder intencional y no algo que funcionó y se rompió al migrar a Odoo 17/OWL?
16. **Todo lo marcado como "pendiente de confirmar en Docker de pruebas"** en la tabla (especialmente `hr_expense.xml` xpath duplicado, y `report/leulit_freelance_actividad_aerea.xml:11` sin guarda de logo) requiere `./upd_module.sh leulit_operaciones dev` y prueba manual — no ejecutable desde este entorno de revisión.
17. **`leulit_16_bravo.py`** — `dp.get_precision('leulit_2d_actividad_dp')`: ¿typo o nombre real definido fuera del alcance de este addon (`leulit_tarea`/`leulit_parte_145`)?
18. **`leulit_meteo_limits.py`** — modelo completamente huérfano (sin ACL, vista, menú ni referencias). ¿Es una funcionalidad en desarrollo activo (p. ej. para integrarse con `leulit_meteo` en un futuro go/no-go automático) o código a eliminar?
