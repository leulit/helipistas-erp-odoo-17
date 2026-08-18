# Especificación funcional y técnica — App móvil "Parte de Vuelo" (`leulit.vuelo`)

**Versión:** 1.0 — 2026-08-18
**Origen:** Odoo 17 Community, ERP Helipistas (`https://erp.helipistas.com`)
**Formulario replicado:** `action 793` (`leulit_operaciones.leulit_20230906_1505_action`, "Partes de Vuelo") → vista form **id 3224**, tree **3228**, kanban **3229**
**Destinatario:** equipo de frontend (Flutter · Android + iOS)

Este documento es la fuente de verdad para el desarrollo. Todo lo que contiene está
extraído del código real de los addons `leulit_*` y verificado contra la base de datos
de producción. Cuando se cita un fichero se cita también la línea.

---

## 0. Decisiones de alcance ya tomadas

| Decisión | Valor |
|---|---|
| Ciclo de vida cubierto | **Completo**: prevuelo → postvuelo → cerrado (+ cancelado), incluidas las dos firmas |
| Integración | **JSON-RPC directo contra Odoo** (`/web/session/authenticate` + `/web/dataset/call_kw`). Sin backend intermedio |
| Conectividad | **Siempre online**. No hay modo offline ni cola de escritura |
| Firma | **El piloto teclea el código OTP**, igual que en el ERP web. No hay firma de un toque ni biometría (§8.2) |
| Alcance de la lista | **Solo los partes propios**: aquellos en los que el usuario es `piloto_id` o `piloto_supervisor_id` — los dos roles que pueden firmar. Sin conmutador "ver todos" (§15) |
| Technical Log y anomalías | **Solo lectura**, filas no pulsables. Su gestión se queda en el ERP web (§4.1 bloques D y E) |

Consecuencia directa de "JSON-RPC directo": **la app debe usar el endpoint `onchange` del
servidor** para todos los cálculos derivados (§6). Replicarlos en cliente es opcional y solo
para feedback instantáneo; el valor que se persiste es siempre el que devuelve el servidor.

---

## 1. Qué es un parte de vuelo

`leulit.vuelo` es el registro operacional de un vuelo. Un mismo registro atraviesa tres
momentos: planificación (prevuelo), ejecución registrada (postvuelo) y cierre contable/legal
(cerrado). Es documento aeronáutico: los datos que contiene alimentan el Technical Log, el
log book del piloto, el control de potencial de la aeronave, la actividad aérea (descansos)
y los partes de escuela.

- **Modelo:** `leulit.vuelo`
- **Tabla:** `leulit_vuelo`
- **Orden por defecto:** `fechavuelo desc`
- **`_rec_name`:** `codigo` (secuencia `leulit.vuelo`, formato `VUL-0019153`)
- **Hereda:** `mail.thread` (chatter con `message_ids`)
- **Total de campos en el modelo:** 221 · **usados en el formulario:** 174
- **Definición base:** `addons/leulit_operaciones/models/leulit_vuelo.py:25`
- **Extensiones:** `leulit_actividad`, `leulit_escuela`, `leulit_seguridad`, `leulit_taller`,
  `leulit_esignature` (cada uno con su `_inherit = "leulit.vuelo"`)

### 1.1 El `codigo` lo asigna el servidor

`create()` (`leulit_vuelo.py:76`) fuerza `create_uid` al usuario actual y genera `codigo`
con `ir.sequence.next_by_code('leulit.vuelo')`. **La app no debe enviar `codigo` ni
`create_uid` en el `create`.**

---

## 2. Máquina de estados — tres campos, no uno

Este es el punto donde más se equivocan las reimplementaciones. Hay **tres** campos de
estado con semánticas distintas:

### 2.1 `estado` — estado real del parte

`Selection`, default `prevuelo`.

| Valor | Etiqueta |
|---|---|
| `prevuelo` | Pre-Vuelo |
| `postvuelo` | Post-Vuelo |
| `cerrado` | Cerrado |
| `cancelado` | Cancelado |

**Nunca se escribe directamente desde la UI.** Solo cambia por:
- firma validada (§8),
- `wizard_cancelar()` → `cancelado`,
- `wizardSetPrevuelo()` → vuelve a `prevuelo`.

### 2.2 `estado_vista` — qué pantalla se está mostrando

`Selection`, default `prevuelo`. Valores: `prevuelo`, `fin_prevuelo`, `postvuelo`,
`cerrado`, `cancelado`.

Es **pura navegación** y se persiste en base de datos. Los botones del header llaman a
métodos que hacen `write({'estado_vista': ...})`:

| Botón | Método (`type="object"`) |
|---|---|
| Prevuelo | `action_cambiar_pantalla_prevuelo` |
| Prevuelo 2 | `action_cambiar_pantalla_fin_prevuelo` |
| Postvuelo | `action_cambiar_pantalla_postvuelo` |
| Cerrado | `action_cambiar_pantalla_cerrado` |
| Cancelado | `action_cambiar_pantalla_cancelado` |

En la app móvil esto se traduce en un **selector de pestañas/pasos**. Se puede resolver en
local (sin RPC) siempre que el valor se persista al guardar; el ERP web lo persiste en cada
clic. Recomendación: replicar el comportamiento del ERP (write inmediato) para que el
usuario que salte al navegador vea la misma pantalla.

Reglas de disponibilidad de los botones (extraídas de la arch de la vista 3224):

- **Prevuelo**: siempre.
- **Prevuelo 2**: siempre.
- **Postvuelo**: oculto si `estado == 'prevuelo'`.
- **Cerrado**: oculto si `estado in ('prevuelo','postvuelo')`.
- **Cancelado**: oculto si `estado in ('prevuelo','postvuelo','cerrado')`.

### 2.3 `control_firma` — estado de la firma electrónica

`Selection`, default `no-firmado`. Valores: `no-firmado`, `pendiente`, `firmado`.
Definido en `addons/leulit_esignature/vuelo.py:509`.

### 2.4 Diagrama real del ciclo

```
                       ┌──────────────────────────────────────────────┐
                       │ estado=prevuelo · control_firma=no-firmado    │
                       │ (creación)                                    │
                       └──────────────────────┬───────────────────────┘
                                              │ botón "Firmar"
                                              │ firmar_doc_parte_vuelo()
                                              │  → wkf_act_postvuelo()  ← CADENA DE 10 VALIDACIONES (§7.1)
                                              │  → write control_firma='pendiente'
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │ estado=prevuelo · control_firma=pendiente     │
                       └──────────────────────┬───────────────────────┘
                                              │ OTP validado
                                              │ leulit_signaturedoc.checksignatureRef()
                                              │  → vuelo.buildPdfSigned()
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │ estado=postvuelo · control_firma=no-firmado   │
                       └──────────────────────┬───────────────────────┘
                                              │ botón "Firmar"
                                              │ firmar_doc_parte_vuelo()
                                              │  → wkf_act_cerrado()    ← CADENA DE 8 VALIDACIONES (§7.2)
                                              │  → verificar_actividad_aerea() por tripulante
                                              │  → write control_firma='pendiente'
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │ estado=postvuelo · control_firma=pendiente    │
                       └──────────────────────┬───────────────────────┘
                                              │ OTP validado → buildPdfSigned()
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │ estado=cerrado · control_firma=firmado        │
                       └──────────────────────────────────────────────┘

  Desde prevuelo o postvuelo:  botón "Cancelar" → wizard_pre_cancelar() → wizard_cancelar()
                               → estado=cancelado (+ parte de escuela asociado a cancelado)

  Desde postvuelo/cerrado/cancelado: botón "Set to Pre-Vuelo" → wizardSetPrevuelo()
                               → estado=prevuelo, p_corregido=True, p_corregido_date=now,
                                 borra documentos de firma, control_firma='no-firmado',
                                 borra parte de escuela y líneas analíticas
```

### 2.5 `can_sign` — cuándo se muestra el botón Firmar

Campo calculado no almacenado (`addons/leulit_esignature/vuelo.py:488`). Lógica exacta:

```python
can_sign = False
vuelos_pendientes = search([('control_firma','=','pendiente'),
                            '|', ('helicoptero_id','=', self.helicoptero_id.id),
                                 ('piloto_id','=', self.piloto_id.id)])
if len(vuelos_pendientes) == 0:
    if estado == 'prevuelo' and control_firma == 'no-firmado':
        can_sign = True
if estado == 'postvuelo' and control_firma == 'no-firmado':
    can_sign = True
if estado == 'cerrado'   and control_firma == 'pendiente':
    can_sign = True
```

Traducción: **no se puede firmar un prevuelo si el mismo helicóptero o el mismo piloto
tienen otro parte con firma pendiente.** La app debe leer `can_sign` del servidor, no
calcularlo (depende de una búsqueda global).

---

## 3. Mapa de pantallas

El formulario del ERP es un único form con bloques que se muestran/ocultan según
`estado_vista`. En móvil se traduce a **4 pantallas + cabecera común + pie común**.

```
┌─ CABECERA (siempre) ────────────────────────────────────────────┐
│ statusbar `estado` · selector de pantalla (§2.2)                │
│ Código (readonly) · Creador (readonly)                          │
│ Acciones: Firmar | Cancelar | Set to Pre-Vuelo | Plan operacional| PTV │
└─────────────────────────────────────────────────────────────────┘

  Pantalla 1  PREVUELO         (estado_vista='prevuelo')
  Pantalla 2  PREVUELO 2       (estado_vista='fin_prevuelo')
  Pantalla 3  POSTVUELO        (estado_vista='postvuelo')
  Pantalla 4  CERRADO/CANCELADO(estado_vista='cerrado'|'cancelado')  → solo lectura

┌─ PIE (siempre) ─────────────────────────────────────────────────┐
│ N.F. (`nv`) + N.F. UID (`nv_uid`) + IFR (`ifr`)                 │
│ ▸ Imputaciones de Tiempo (`account_analytic_lines`, colapsable) │
│ ▸ Documentos Firmados (`esignature_docs`, colapsable)           │
│ Chatter (`message_ids`)                                         │
└─────────────────────────────────────────────────────────────────┘
```

### 3.1 Barra de acciones (cabecera)

| Botón | Método | Visible cuando | Tipo |
|---|---|---|---|
| Set to Pre-Vuelo | `wizardSetPrevuelo` | `estado in ('cerrado','cancelado','postvuelo')` | object |
| Firmar | `firmar_doc_parte_vuelo` | `can_sign` | object |
| Cancelar | `wizard_pre_cancelar` | `estado not in ('cerrado','cancelado')` | object (abre confirmación) |
| Plan operacional | `vuelo_print` | siempre | object (abre popup ficha) |
| PTV | `parte_vuelo_print` | `estado not in ('prevuelo','cancelado')` | object (informe PDF) |

`wizard_pre_cancelar` devuelve una `ir.actions.act_window` de confirmación; en móvil se
sustituye por un diálogo nativo que, al confirmar, llama a **`wizard_cancelar`**.

---

## 4. Catálogo completo de campos por bloque

Convenciones de la tabla:
- **RO**: condición bajo la que el campo es de solo lectura (expresión Odoo tal cual).
- **Vis**: condición de visibilidad (si está vacío, siempre visible dentro de su bloque).
- **Widget**: widget del ERP; equivalente móvil en §5.
- Los campos marcados **`force_save`** son readonly en la vista pero **se persisten**: en el
  ERP los rellena el `onchange`. La app debe enviarlos en el `write` con el valor que
  devolvió el `onchange` del servidor.

### 4.0 Campos ocultos siempre presentes (necesarios para la lógica)

Se leen y se mantienen en memoria; no se pintan.

`wbdata`, `is_it_developer`, `p_corregido`, `p_corregido_date`, `wbimage`, `wbokey`, `id`,
`emptyweight`, `longmoment`, `latmoment`, `longarm`, `latarm`, `pesomax`, `deltahoras`,
`helicoptero_tipo`, `parte_escuela_id`, `night_hours`, `peso_piloto`, `peso_alumno`,
`is_comercial_uid`, `nombre_actividad`, `active`, `estado_vista`, `can_sign`,
`pasajeros_wb`, `performance`, `weight_and_balance_id`, `non_conformity_count`, `nv_date`.

---

### 4.1 PANTALLA 1 · PREVUELO

#### Bloque A — Datos generales (aeronave)

`Vis` del bloque: `estado_vista not in ('postvuelo','cerrado','cancelado')`

| Campo | Etiqueta | Tipo | Req | RO | Notas |
|---|---|---|---|---|---|
| `helicoptero_id` | Helicóptero | m2o `leulit.helicoptero` | **sí** | `estado in ('postvuelo','cerrado','cancelado')` | domain `[('baja','=',False)]`; `no_create`, `no_open`. **Dispara onchange masivo (§6.1)** |
| `helicoptero_modelo` | Modelo | char (compute) | — | RO | `helicoptero_id.modelo.name` |
| `helicoptero_tipo` | Tipo | selection (related, store) | — | RO | `AS350`,`EC120B`,`EC130`,`R22`,`R44`,`CABRI G2`,`DJI` |
| `strhoras_remanente` | Potencial Aeronave | char (related) | — | RO | Vis: `helicoptero_id` |
| `semaforo` | Estado Aeronave | char (related) | — | RO | widget `semaforo_char` (`red`/`orange`/`green`). Vis: `helicoptero_id` |

#### Bloque B — Fecha, presupuesto y checks

| Campo | Etiqueta | Tipo | Req | RO | Vis |
|---|---|---|---|---|---|
| `fechavuelo` | Fecha de vuelo | date | **sí** (default hoy) | `estado in ('postvuelo','cerrado','cancelado')` | `estado_vista not in ('postvuelo','cerrado','cancelado')` |
| `checklist_postvuelo_realizado` | Debriefing con los tripulantes / Inspección postvuelo realizada | bool | — | `estado in ('prevuelo','cerrado','cancelado')` | `estado_vista not in ('prevuelo','cerrado','cancelado')` |
| `presupuesto_vuelo` | Presupuesto | m2o `sale.order` | — | `estado in ('cancelado',)` | `estado_vista != 'cancelado'` · domain `[('flag_flight_part','=',True),('state','=','sale'),('task_done','=',False)]` |
| `checklist_realizado` | Inspección prevuelo realizada | bool | — | `estado in ('postvuelo','cerrado','cancelado')` | `estado_vista not in ('postvuelo','cerrado','cancelado')` |
| `checklist_prevuelo_BFF` | Inspección prevuelo BFF | bool (default **True**) | — | — | `checklist_realizado and helicoptero_tipo in ('EC120B','CABRI G2')` |
| `checklist_prevuelo_entre_vuelos` | Inspección entre vuelos | bool | — | — | idem anterior |
| `briefing_realizado` | Briefing con los tripulantes / Briefing Salida, Llegada y Alternativo | bool | — | `estado in ('postvuelo','cerrado','cancelado')` | `estado_vista != 'cancelado'` |

**Regla de exclusión mutua BFF ↔ entre vuelos** (`leulit_vuelo.py:2128-2140`):
```
onchange checklist_prevuelo_BFF:            si True → entre_vuelos=False, si False → entre_vuelos=True
onchange checklist_prevuelo_entre_vuelos:   si True → BFF=False,          si False → BFF=True
```

#### Bloque C — Salida, llegada, tiempos previstos, alternativos

`Vis` del bloque: `estado_vista not in ('cerrado','cancelado')`

| Campo | Etiqueta | Tipo | Req | RO | Vis | Widget |
|---|---|---|---|---|---|---|
| `lugarsalida` | Lugar salida | m2o `leulit.helipuerto` | no | `estado in ('postvuelo','cerrado','cancelado') or not is_comercial_uid` | `estado_vista not in ('postvuelo','cerrado','cancelado')` | selector |
| `horasalida` | Hora salida local | float | **sí** | `estado in ('cerrado','cancelado')` | — | `float_time` |
| `utc_horasalida` | Hora salida UTC | char (compute) | — | RO | — | texto |
| `tiempoprevisto` | Tiempo de vuelo previsto | float | **sí** | `estado in ('postvuelo','cerrado','cancelado')` | `estado_vista not in ('postvuelo','cerrado','cancelado')` | `float_time` |
| `velocidadprevista` | Vel. Prevista (KT) | float | — | RO **force_save** | idem | número |
| `distanciatotalprevista` | Dist. Prevista (NM) | float | — | RO **force_save** | idem | número |
| `lugarllegada` | Lugar llegada | m2o `leulit.helipuerto` | **sí** | `estado in ('cerrado','cancelado') or not is_comercial_uid` | — | selector |
| `horallegadaprevista` | Hora Llegada prevista local | float | — | RO **force_save** | `estado_vista not in ('postvuelo','cerrado','cancelado')` | `float_time` |
| `utc_horallegadaprevista` | Hora llegada prevista UTC | char (compute) | — | RO | idem | texto |
| `alternativos` | Alternativos | o2m `leulit.helipuerto` | — | `estado in ('postvuelo','cerrado','cancelado') or not is_comercial_uid` | idem | `many2many_tags` (`no_create`, `edit:false`) |

> **Ojo con `velocidadprevista` y `distanciatotalprevista`:** en la vista son readonly pero
> `force_save="1"`. `velocidadprevista` la rellena el onchange de helicóptero
> (`helicoptero_id.velocidad`). `distanciatotalprevista` la rellena el onchange de ruta o el
> de `tiempoprevisto`. **Sin ruta, la única forma de que la distancia deje de ser 0 es
> editar `tiempoprevisto`** (§6.3); y `distanciatotalprevista == 0` bloquea el paso a
> postvuelo (§7.1). Ver aviso en §12.

> **`alternativos` es un One2many, no un Many2many**, pese al widget `many2many_tags`:
> `leulit.helipuerto.vuelo_id` es la inversa. Añadir un alternativo **modifica el registro
> del helipuerto**. Se manipula con comandos `(4, id)` / `(3, id)`.

#### Bloques D y E — Technical Log y anomalías: **solo lectura** (decisión 2026-08-18)

Ambos bloques son **exclusivamente informativos en la app**: se muestran, no se editan y
**no se abre la ficha del registro**. La gestión de anotaciones y anomalías sigue haciéndose
en el ERP web.

**Bloque D — Anotaciones Technical Log**
`Vis`: `anotacion_ids` no vacío. o2m **calculado no almacenado** sobre
`leulit.anotacion_technical_log`. Columnas: `codigo`, `anotacion`.
Si hay anotaciones, **el parte no puede pasar a postvuelo** (§7.1-5, mensaje
`Este helicóptero tiene una anotación activa y no puede ser utilizado`). Por eso, aunque sea
solo lectura, **el bloque debe ser visible y destacado**: explica por qué la firma va a fallar.

**Bloque E — Anomalías / Discrepancias**
`Vis`: `diferido_ids` no vacío. o2m **calculado no almacenado** sobre `leulit.anomalia`.
Columnas: `codigo`, `discrepancia`, `estado`.
Una anomalía sin firmar bloquea el helicóptero (`isHelicopterBlocked`) tanto en el onchange
de helicóptero (§6.1) como en el paso a postvuelo y a cerrado (§7.1-5, §7.2-4).

Consecuencias técnicas de que ambos campos sean `compute` sin `inverse`:
- **Nunca se envían en un `create` ni en un `write`.** Ya están en la lista de exclusión de
  `toWriteValues` (§11.3). Enviarlos daría error.
- No admiten crear, editar ni borrar líneas desde ningún cliente.

> Diferencia deliberada con el ERP web: allí la lista de anomalías declara `edit="true"` y al
> pulsar una fila se abre la ficha de `leulit.anomalia`. **La app no lo hace**: las filas no
> son pulsables. Es una restricción intencionada, no un olvido.

#### Bloque F — Tripulantes

`Vis` del bloque: `estado_vista not in ('postvuelo','cerrado','cancelado')`

| Campo | Etiqueta | Tipo | RO | Notas |
|---|---|---|---|---|
| `numtripulacion` | Nº tripulantes | int (default 1) | `estado in ('postvuelo','cerrado','cancelado')` | |
| `numpax` | Nº de pax / AESA | int | idem | |
| `numpae` | Num. AL/PA/PE/PAE/PO | int | idem | |
| `asiento_pic` | PIC Asiento | selection `pic_right`/`pic_left` (default `pic_right`) | idem | |
| `vuelo_tipo_line` | Tipo Vuelo | o2m `leulit.vuelo_tipo_line` | `estado in ('postvuelo','cerrado','cancelado') and not is_it_developer` | lista editable, columna `vuelo_tipo_id` (m2o `leulit.vuelostipo`, `no_create`) |

Tarjetas de tripulantes (cada una con m2o + foto colapsable):

| Rol | Campo | Modelo | Foto | Visible si | Extra |
|---|---|---|---|---|---|
| Piloto | `piloto_id` (**requerido**) | `leulit.piloto` | `foto_piloto` | siempre | `semaforo_pf_piloto` (widget `semaforo_char`, oculto si `== 'N/A'`) |
| Operador | `operador` | `leulit.operador` | `foto_operador` | siempre | `semaforo_pf_operador` (ídem) |
| PIC Verificado | `verificado` | `leulit.piloto` | `foto_verificado` | `alumno == False` | |
| Alumno | `alumno` | `leulit.alumno` | `foto_alumno` | `not verificado` | domain `[('piloto_id','!=',False)]` |
| PIC Supervisor | `piloto_supervisor_id` | `leulit.piloto` | `foto_piloto_supervisor_id` | siempre | |

Todos con `no_create`, `no_create_edit`, `no_open`. RO: `estado in ('postvuelo','cerrado','cancelado')`.

Reglas asociadas:
- `onchange verificado` → si hay verificado, `numtripulacion = 2`; si no, `1`
  (`leulit_vuelo.py:2142`).
- `doblemando` (compute almacenado, `leulit_escuela/models/leulit_vuelo.py:171`) = `True`
  si hay `piloto_id` **y** `alumno` **y** sus `partner_id` son distintos.
- `onchange doblemando` → `asiento_pic = 'pic_left'` si `doblemando`, si no `'pic_right'`.
- `semaforo_pf_*`: verde / rojo / `N/A` según los perfiles de formación del tripulante
  (`leulit_escuela/models/leulit_vuelo.py:179`). Se lee del servidor, no se calcula.

#### Bloque G — Escuela

`Vis`: `(alumno or verificado) and estado_vista not in ('cancelado','cerrado')`

| Elemento | Detalle |
|---|---|
| Botón "Añadir Silabus" | `wizard_add_parte_escuela` (object). Oculto si `estado in ('cancelado','cerrado')` |
| `silabus_ids` | o2m `leulit.rel_parte_escuela_cursos_alumnos`, `limit:3`, sin crear desde la lista |
| `valoracion_escuela` | selection `1..5`, `apto`, `noapto`. Oculto en `estado_vista == 'prevuelo'`. RO si `estado in ('cerrado','cancelado')` |
| `comentario_escuela` | text. Misma visibilidad/RO |

Columnas de `silabus_ids`: `rel_curso`, `rel_silabus`, `valoracion` (visible si
`sil_valoracion`), `nota` (visible si `sil_test`), botón `add_docs_rel_parte_escuela`
(visible si `sil_test`). Columnas ocultas de control: `sil_test`, `sil_valoracion`,
`todo_cerrar`, `rel_docs`.
Decoración: verde si `todo_cerrar == False`, ámbar si `True`.

#### Bloque H — Combustible (planificación)

`Vis` del bloque: `estado_vista not in ('postvuelo','cerrado','cancelado')`

Se presenta como una rejilla de tarjetas. Cada magnitud tiene **tres campos**: litros
(editable o calculado), kilos y galones (siempre readonly `force_save`, colapsables).

| Tarjeta | Campo litros | RO litros | kg | gal |
|---|---|---|---|---|
| Combustible (parámetros) | `reservasfuel` sel `10`/`20`/`30` min (def `30`)<br>`rodaje` sel `0`/`2`/`5` min (def `0`)<br>`contingencia` sel `0`/`5` % (def `0`)<br>`distancia_alternativo` float | `estado != 'prevuelo'` | — | — |
| Aceite | `oilqty` (default **-1**) | `estado != 'prevuelo'` | `oilqty_kg` | `oilqty_gal` (default -0.26) |
| Fuel remanente | `editfuelrem` | `estado != 'prevuelo'` | `fuelremanente_kg` | `fuelremanente_gal` |
| Fuel añadido | `fuelqty` | `estado != 'prevuelo'` | `fuelqty_kg` | `fuelqty_gal` |
| Fuel salida | `fuelsalida` | **RO force_save** | `fuelsalida_kg` | `fuelsalida_gal` |
| Previsto aterrizaje | `combustiblelanding` | **RO force_save** | `combustiblelanding_kg` | `combustiblelanding_gal` |
| Combustible extra | `combustibleextra` | **RO force_save** | `combustibleextra_kg` | `combustibleextra_gal` |
| Consumo medio | `consumomedio_vuelo` (l/min) | `estado != 'prevuelo'` | `consumomedio_vuelo_kg` | `consumomedio_vuelo_gal` |
| Fuel trayecto | `combustibletrayecto` (compute) | RO | `combustibletrayecto_kg` | `combustibletrayecto_gal` |
| Fuel mínimo | `combustibleminimo` | **RO force_save** | `combustibleminimo_kg` | `combustibleminimo_gal` |
| Tacom | `tacomsalida` | `estado != 'prevuelo'` | — | — · **oculto si `helicoptero_tipo == 'EC120B'`** |

> `oilqty` con default `-1` es deliberado: la validación de paso a postvuelo exige
> `oilqty >= 0`, es decir, obliga al piloto a introducir explícitamente la cantidad
> (0 es un valor válido, -1 significa "no informado").

#### Bloque I — Ruta y aerovías

`Vis`: `estado_vista not in ('postvuelo','cerrado','cancelado')`

| Campo | Tipo | RO |
|---|---|---|
| `ruta_id` | m2o `leulit.ruta`, domain `[('activo','=',True)]`, `no_create`/`no_open` | `estado in ('postvuelo','cerrado','cancelado')` |
| `aerovia_ids` | o2m `leulit.rel_planoperacional_aerovia` — **lista solo lectura** (`create=false edit=false delete=false`), visible solo si hay `ruta_id` | — |

Columnas de `aerovia_ids`: `aerovia_id`, `distancia` (con suma), `rumbo`,
`altitudprevista`, `altitudseguridad`, `tiempoprevisto` (`float_time`, con suma).

#### Bloque J — Equipos de emergencia

`Vis`: `estado_vista not in ('postvuelo','cerrado','cancelado')`.
`balsa`, `flotadores`, `chalecos` — booleanos. RO si `estado in ('postvuelo','cerrado','cancelado')`.

> Si `ruta_id.water_zone` es `True`, `flotadores` **debe** estar marcado o el paso a
> postvuelo falla (§7.1).

---

### 4.2 PANTALLA 2 · PREVUELO 2 (`estado_vista == 'fin_prevuelo'`)

Es la única pantalla donde el bloque grande de prevuelo está oculto.

#### Pestaña "Meteorología / Notam"

| Campo | Tipo | RO |
|---|---|---|
| `indicativometeo` | char (lista OACI separada por comas) | `estado in ('postvuelo','cerrado','cancelado')` |
| Botón "Obtener meteo" | `action_obtener_meteo_salida` (object) | oculto si `estado in ('postvuelo','cerrado','cancelado')` |
| `meteo` | text (METAR + TAF crudos) | idem |
| `notam_revisado` | bool | idem |
| `notaminfo` | html **force_save** | idem |

`_onchange_lugares_indicativo_meteo` (`leulit_vuelo.py:2149`): al cambiar `lugarsalida` o
`lugarllegada`, si el `name` del helipuerto son 4 letras y no está en
`{ZZZZ, XXXX, AAAA, NNNN}`, se autocompleta `indicativometeo` con los códigos OACI
separados por coma.

`action_obtener_meteo_salida` (`leulit_vuelo.py:1497`):
- parte `indicativometeo` por comas, normaliza a mayúsculas;
- si queda vacío → `UserError: 'Introduce un indicativo OACI en el campo "Indicativo meteo".'`
- por cada OACI llama a `leulit.meteo.metar.briefing_oaci(icao, fecha=fechasalida)`;
- concatena `raw_metar` + `raw_taf` separados por `\n\n`, y los bloques de distintos
  aeropuertos por `\n\n==============================\n\n`;
- si ningún OACI da datos → `UserError`;
- devuelve una acción cliente `display_notification` con título "Meteorología actualizada",
  tipo `success` o `warning` (y `sticky`) si hubo OACIs sin datos.

**La app debe manejar respuestas de tipo `ir.actions.client` / `display_notification`**
mostrando un snackbar con `params.title`, `params.message` y `params.type`.

Enlaces informativos de la pestaña: Mapa NOTAM `https://insignia.enaire.es/`,
fuente NOTAM ICAO iSTARS.

#### Pestaña "Comentarios"

`comentarios` — text libre.

#### Weight and Balance

| Elemento | Detalle |
|---|---|
| Botón "Weight and Balance" | `wizard_add_wb` (object) → abre el editor de W&B (§9) |
| `valid_takeoff_longcg` | bool related, widget `semaforo_bool`, RO |
| `valid_takeoff_latcg` | ídem |
| `valid_landing_longcg` | ídem |
| `valid_landing_latcg` | ídem |

#### Performance

Botón "Performance" → `button_performance_vuelo` (object). Ver §10.

---

### 4.3 PANTALLA 3 · POSTVUELO (`estado_vista == 'postvuelo'`)

Visible el bloque de cabecera reducido (fecha oculta, checks de prevuelo ocultos,
`checklist_postvuelo_realizado` visible, `presupuesto_vuelo` visible, `briefing_realizado`
visible) más el bloque siguiente.

`Vis` del bloque de datos de postvuelo: `estado_vista not in ('cerrado','cancelado','prevuelo')`

| Tarjeta | Campo | Tipo | Req | RO | Widget |
|---|---|---|---|---|---|
| Tiempos | `tiemposervicio` | float | **sí si `estado in ('postvuelo','cancelado')`** | `estado in ('prevuelo','cerrado','cancelado')` | `float_time` |
| | `airtime` | float | **sí si `estado == 'postvuelo'`** | `estado != 'postvuelo'` | `float_time` |
| | `horallegada` | float | — | RO **force_save** | `float_time` |
| | `utc_horallegada` | char compute | — | RO | texto |
| Tacom (si `helicoptero_tipo != 'EC120B'`) | `tacomsalida` | float | — | `estado != 'prevuelo'` | número |
| | `tacomllegada` | float | — | `estado != 'postvuelo'` | número |
| NG/NF (si `helicoptero_tipo == 'EC120B'`) | `ngvuelo` | float | — | `estado != 'postvuelo'` | número |
| | `nfvuelo` | float | — | `estado != 'postvuelo'` | número |
| | `arlanding` | int (Autorotation Landings) | — | `estado != 'postvuelo'` | número |
| Combustible llegada | `fuelllegada` | float | — | `estado != 'postvuelo'` | número |
| | `fuelllegada_kg` / `fuelllegada_gal` | float | — | RO force_save | colapsable |
| Gancho | `uso_gancho` | float | — | `estado != 'postvuelo'` | `float_time` |
| | `sling_cycle` | int | — | `estado != 'postvuelo'` | número |
| Landings | `landings` (Day, default 1) | int | — | `estado != 'postvuelo'` | número |
| | `nightlandings` (Night, default 0) | int | — | `estado != 'postvuelo'` | número |

En esta pantalla sigue visible el bloque **Escuela** (§4.1 G) si hay alumno o verificado, y
ahí es donde `valoracion_escuela` y `comentario_escuela` dejan de estar ocultos.

---

### 4.4 PANTALLA 4 · CERRADO / CANCELADO

Todos los bloques operativos quedan ocultos. Se muestra solo la cabecera, el pie común
(§3) y, en su caso, las anotaciones y anomalías. **Pantalla de solo lectura.**

---

### 4.5 PIE COMÚN (todas las pantallas)

| Campo | Tipo | Notas |
|---|---|---|
| `nv` | bool "No Volado" | onchange: si `nv` → `nv_uid=False`, `nv_date=False`; si no → `nv_uid=uid`, `nv_date=now` (invertido respecto a lo intuitivo, ver §12) |
| `nv_uid` | m2o `res.users` | visible si `not nv` |
| `ifr` | bool | |
| `account_analytic_lines` | o2m `account.analytic.line`, RO | columnas `employee_id`, `partner_id`, `idmodelo`, `modelo`, `name`, `unit_amount` (widget `timesheet_uom`) |
| `esignature_docs` | o2m `leulit_signaturedoc`, RO | columnas `firmado_por`, `referencia`, `attachment_id` (filename `name_attach`) |
| `message_ids` | chatter | widget `mail_thread` |

---

## 5. Equivalencias de widget

| Widget Odoo | Comportamiento | Equivalente móvil |
|---|---|---|
| `float_time` | float donde la parte entera son horas y la decimal fracción de hora. `2.5` = `02:30` | `TimePicker` o campo `HH:MM` con conversión (§6.7) |
| `semaforo_char` | pinta un círculo rojo/ámbar/verde según el valor `'red'`/`'orange'`/`'green'`; `'N/A'` se oculta | Indicador de color |
| `semaforo_bool` | círculo verde si `True`, rojo si `False` | Indicador de color |
| `image` | binario base64 | `Image.memory(base64Decode(...))` |
| `many2many_tags` | chips | chips con eliminación |
| `html` | HTML | visor HTML solo lectura |
| `timesheet_uom` | duración en formato de la compañía | texto `HH:MM` |
| `mail_thread` | chatter | lista de mensajes + adjuntos |
| statusbar | pasos de `estado` | Stepper horizontal, no interactivo |

---

## 6. Lógica derivada — qué recalcula el servidor y cuándo

**Regla de oro: todo campo con `on_change="1"` en la vista dispara una llamada `onchange` al
servidor.** La app *debe* hacer esa llamada (§11.4) y aplicar el resultado. Las fórmulas de
abajo se documentan para poder dar feedback inmediato y para poder validar en test que
cliente y servidor coinciden.

Campos que disparan onchange en el formulario:
`helicoptero_id`, `helicoptero_tipo`, `fechavuelo`, `lugarsalida`, `lugarllegada`,
`horasalida`, `tiempoprevisto`, `velocidadprevista`, `distanciatotalprevista`,
`horallegadaprevista`, `horallegada`, `ruta_id`, `reservasfuel`, `rodaje`, `contingencia`,
`distancia_alternativo`, `consumomedio_vuelo`, `editfuelrem`, `fuelqty`, `fuelllegada`,
`oilqty`, `tiemposervicio`, `nightlandings`, `piloto_id`, `operador`, `verificado`,
`alumno`, `piloto_supervisor_id`, `doblemando`, `vuelo_tipo_line`, `estado`, `nv`,
`checklist_prevuelo_BFF`, `checklist_prevuelo_entre_vuelos`, `weight_and_balance_id`,
`presupuesto_vuelo`, `parte_escuela_id`.

### 6.1 `onchange helicoptero_id` — el más importante

`leulit_vuelo.py:1550`. Además de devolver valores, **escribe en base de datos** (`item.write(values)`)
y **borra el registro de Performance asociado** (`obj_perf.unlink()`).

1. Si `isHelicopterBlocked(helicoptero_id, fechavuelo)` (hay anomalía sin firmar) →
   devuelve solo un **warning**:
   `{'title': 'Warning', 'message': 'Este helicoptero tiene una anomalía/discrepancia sin firmar y no puede ser utilizado'}`
   y **no** rellena nada. La app debe mostrar el aviso.
2. Si no, busca el **último vuelo cerrado de ese helicóptero** (`order='fechasalida desc', limit=1`)
   y toma de él `tacomllegada`, `fuelllegada` y `lugarllegada`.
3. Rellena:

| Campo destino | Origen |
|---|---|
| `emptyweight` | `helicoptero_id.emptyweight` |
| `longmoment` | `helicoptero_id.longmoment` |
| `latmoment` | `helicoptero_id.latmoment` |
| `longarm` | `helicoptero_id.longarm` |
| `latarm` | `helicoptero_id.latarm` |
| `pesomax` | `helicoptero_id.pesomax` |
| `helicoptero_modelo` | `helicoptero_id.modelo.name` |
| `helicoptero_tipo` | `helicoptero_id.tipo` |
| `velocidadprevista` | `round(helicoptero_id.velocidad, 2)` |
| `editfuelrem`, `fuelremanente`, `fuelsalida`, `combustibleextra` | `fuelllegada` del último vuelo cerrado |
| `consumomedio_vuelo` | `helicoptero_id.consumomedio` |
| `lugarsalida` | `lugarllegada` del último vuelo cerrado |
| `tacomsalida` | `tacomllegada` del último vuelo cerrado |
| `performance` | `None` (se borra) |

### 6.2 `onchange ruta_id`

`leulit_vuelo.py:1608`. Borra las aerovías actuales y las regenera desde
`ruta_id.aerovia_ids`:

```
distanciatotal        = Σ av.distancia
tiempo_previsto_total = Σ round(get_tiempo_vuelo_decimal(av.distancia, velocidadprevista), 2)

por cada aerovía crea (0,0,{ruta_id, aerovia_id, aerovia_ruta_id, vuelo_id,
                            tiempoprevisto: round(tp,2), altitudprevista: av.altitudprevista})

tiempoprevisto          = tiempo_previsto_total
distanciatotalprevista  = round(distanciatotal, 2)
```

Si `ruta_id` queda vacío, no devuelve valores (las aerovías se borran igualmente).

### 6.3 `calculosFuel(field)` — motor de combustible

`leulit_vuelo.py:1709`. Se invoca desde los onchange de: `velocidadprevista`,
`horallegadaprevista`, `distanciatotalprevista`, `tiempoprevisto`, `horasalida`,
`reservasfuel`, `consumomedio_vuelo`, `rodaje`, `contingencia`, `distancia_alternativo`,
`helicoptero_tipo`, `editfuelrem`, `fuelqty`, `fuelllegada`.

**Paso 1 — reconciliación distancia/tiempo (solo si NO hay `ruta_id`):**
```
si field ∈ {velocidadprevista, distanciatotalprevista}:
    tiempoprevisto = round(get_tiempo_vuelo_decimal(distanciatotalprevista, velocidadprevista), 2)

si field == tiempoprevisto:
    vv = velocidadprevista * 0.51444444444                       # kt → m/s
    distanciatotalprevista = round(vv * (tiempoprevisto * 3600) * 0.000539956803, 2)   # m → NM
```

**Paso 2 — combustible mínimo** (`_calc_combustible_minimo`, `leulit_vuelo.py:1785`):
```
rodaje         = 0 si falsy
contingencia   = 0 si falsy
distancia_alt  = 0 si falsy

tiempo_a_alternativo = get_tiempo_vuelo_decimal(distancia_alternativo, velocidadprevista)
rodaje_h             = leulit_str_to_float_time(leulit_float_minutes_to_str(float(rodaje)))   # min → horas
tiempo               = tiempoprevisto + rodaje_h + tiempo_a_alternativo

si contingencia == '5':  tiempo = tiempo * 1.05

minutosprevistos  = leulit_float_time_to_minutes(tiempo)
combustibleminimo = round(consumomedio_vuelo * (minutosprevistos + float(reservasfuel)), 2)
```

**Paso 3 — resto de magnitudes:**
```
fuelsalida        = round(editfuelrem + fuelqty, 2)
combustibleextra  = fuelsalida - combustibleminimo

horallegadaprevista = horasalida + tiempoprevisto
si horallegadaprevista >= 24.0: horallegadaprevista -= 24.0

minutosprevistos  = leulit_float_time_to_minutes(tiempoprevisto)
combustiblelanding = fuelsalida - (consumomedio_vuelo * minutosprevistos)

combustibletrayecto = round(consumomedio_vuelo * leulit_float_time_to_minutes(tiempoprevisto), 2)
```

**Paso 4 — derivados kg/gal** para: `combustibleminimo`, `fuelsalida`, `combustiblelanding`,
`combustibleextra`, `editfuelrem` (→ `fuelremanente_*`), `fuelqty`, `fuelllegada`,
`consumomedio_vuelo`, `combustibletrayecto`, usando `convert_litros_to_kg` /
`convert_litros_to_gal` con `helicoptero_tipo` (§6.6).

**Paso 5 — invalidación:** si `estado == 'prevuelo'` y `field` **no** es `horasalida` ni
`horallegadaprevista`:
```
weight_and_balance_id = False
performance           = False
```
Es decir: **tocar cualquier parámetro de combustible invalida el W&B y el Performance ya
calculados.** La UI debe avisar de ello y volver a poner los semáforos en rojo.

### 6.4 `onchange oilqty`

```
oilqty_kg  = convert_litros_to_kg(oilqty, helicoptero_tipo)
oilqty_gal = convert_litros_to_gal(oilqty, helicoptero_tipo)
```

### 6.5 `onchange tiemposervicio` (postvuelo)

`leulit_vuelo.py:1819`:
```
horallegada = horasalida + tiemposervicio;  si >= 24.0 → -24.0
fuelllegada = round(fuelsalida - consumomedio_vuelo * leulit_float_time_to_minutes(tiemposervicio), 2)
```

### 6.6 Conversiones de unidades (`addons/leulit/utilitylib.py`)

```python
DENSIDAD_COMBUSTIBLE = {'R44': 0.71, 'R22': 0.71, 'EC120B': 0.79, 'CABRI G2': 0.71}

convert_litros_to_kg(litros, tipo)  = round(litros * DENSIDAD.get(tipo, 0), 2)   # 0 si el tipo no está
convert_litros_to_gal(litros, tipo) = round(litros * 0.264172, 2)                # el tipo se ignora

convert_nudos_metros_por_segundo(kt) = kt * 0.51444444444
convert_metros_nauticmiles(m)        = m * 0.000539956803
convert_nauticmiles_metros(nm)       = nm * 1852
convert_metros_por_segundo_nudos(ms) = ms * 1.94384

get_tiempo_vuelo_segundos(nm, kt) = (nm*1852) / (kt*0.51444444444)  si kt > 0, si no 0
get_tiempo_vuelo_decimal(nm, kt)  = get_tiempo_vuelo_segundos(nm, kt) / 3600  si > 0, si no 0
```

> **Atención:** para `AS350`, `EC130`, `DJI` la densidad **no está en el diccionario**, así
> que `convert_litros_to_kg` devuelve **0**. Es el comportamiento actual del ERP; la app debe
> reproducirlo tal cual, no "arreglarlo".

### 6.7 Tiempo en formato float (`float_time`)

```python
leulit_float_time_convert(v):
    factor = -1 si v < 0 else 1
    val    = abs(v)
    horas   = factor * floor(val)
    minutos = round((val % 1) * 60)
    si minutos >= 60: minutos = 0; horas += 1
    → (horas, minutos)

leulit_float_time_to_str(v)      = "HH:MM"            # None → "00:00"
leulit_float_time_to_minutes(v)  = horas*60 + minutos
leulit_float_minutes_to_str(v)   = leulit_float_time_to_str(v / 60)
leulit_str_to_float_time("H:M:S")= H + M/60 + S/3600
```

Ejemplos de test obligatorios: `2.5 → "02:30"`, `1.99 → "01:59"`, `0.999 → "01:00"`,
`-1.5 → "-01:30"` (con `factor` negativo aplicado solo a las horas).

### 6.8 Horas UTC

```python
getStrTimeUTC(fecha, hora_float, tz_del_helipuerto)
```
`utc_horasalida` usa `lugarsalida.tz`, `utc_horallegada` y `utc_horallegadaprevista` usan
`lugarllegada.tz`. Son `char` calculados no almacenados: **se leen, no se calculan en la app**.

### 6.9 Cruce de medianoche

`_calc_fecha_llegada` (`leulit_vuelo.py:1225`): si `horallegada` normalizada `< horasalida`,
la fecha de llegada es `fechavuelo + 1 día`. La app debe mostrar la fecha de llegada así
en el resumen.

---

## 7. Validaciones del servidor — el corazón del flujo

Estas validaciones **no** se ejecutan al guardar: se ejecutan al pulsar **Firmar**. Todas
lanzan `UserError` con mensaje en castellano, que la app debe mostrar íntegro al usuario
(§11.6). Se ejecutan **en orden** y la primera que falla aborta.

### 7.1 Cadena PREVUELO → POSTVUELO (`wkf_act_postvuelo`)

`initChainToPostvuelo` (`leulit_vuelo.py:897`), handlers en
`addons/leulit_operaciones/vuelo_chain_postvuelo.py`. Orden real:

**1. `ComprobacionTripulacionEnVuelosPostvueloHandler`**
Ningún tripulante (`piloto_id`, `operador`, `verificado`, `alumno`) puede estar en otro
parte en estado `postvuelo`.
→ `Este vuelo no puede pasar a postvuelo. EL PILOTO ESTÁ EN UN VUELO EN ESTADO POST-VUELO`
(o `EL OPERADOR/VERIFICADO/ALUMNO ...`).

**2. `ComprobacionChecksHandler`**
- `checklist_realizado` debe ser `True`
  → `NO HA MARCADO LA INSPECCIÓN PREVUELO CÓMO REALIZADA`
- `check_first_flight()`: si `helicoptero_tipo in ('EC120B','CABRI G2')`:
  - si ya hay un vuelo cerrado del mismo helicóptero ese día y este es posterior →
    exige `checklist_prevuelo_entre_vuelos`
    → `Este helicóptero ya ha tenido un vuelo hoy. Se debe hacer la inspección entre vuelos. Vuelo anterior: {codigo}`
  - si no hay vuelo previo → exige `checklist_prevuelo_BFF`
    → `Primer vuelo de este helicóptero hoy. Se debe hacer la inspección prevuelo BFF`
- `briefing_realizado` debe ser `True`
  → `NO HA MARCADO EL BRIEFING AERODROMO SALIDA, LLEGADA Y ALTERNATIVOS CÓMO REALIZADO`

**3. `ComprobacionTripulantesTipoActividadHandler`**
- si `numpax > 0` y `tipo_actividad not in ('AOC','NCO')`
  → `Los unicos tipos de vuelo que pueden tener pasajeros son AOC y NCO.`
- si `numpae > 0` y `tipo_actividad in ('AOC','NCO')`
  → `Los tipos de vuelo AOC y NCO no pueden tener tripulantes con funciones en el vuelo.`

(`tipo_actividad` = `vuelo_tipo_line[0].vuelo_tipo_id.tipo_trabajo`.)

**4. `ComprobacionUsuarioPilotoHandler`**
El usuario conectado debe ser el `res.users` del `piloto_id` o del `piloto_supervisor_id`.
→ `Solo el piloto o el piloto supervisor pueden cambiar el estado del vuelo a postvuelo`

**5. `ComprobacionHelicopteroHandler`**
- `helicoptero_id.statemachine != 'En taller'` → `Este helicóptero está en Taller`
- no puede haber anomalía sin firmar → `Este helicóptero tiene una anomalía/discrepancia sin firmar y no puede ser utilizado`
- `anotacion_ids` debe estar vacío → `Este helicóptero tiene una anotación activa y no puede ser utilizado`

**6. `ComprobacionOverlapPartesEscuelaVueloHandler`**
- no puede haber otro parte del mismo helicóptero con `fechasalida >=` esta y estado
  distinto de `cancelado`/`prevuelo`
  → `Existe un parte de vuelo con el mismo helicóptero, posterior a la fecha indicada, en estado Post-Vuelo. Parte de vuelo: {codigo}`
- no puede haber otro parte del mismo helicóptero con `fechasalida <=` esta en `prevuelo`
  → `... anterior a la fecha indicada, en estado Prevuelo. ...`
- no puede haber otro parte del mismo piloto con `fechasalida <=` esta en `prevuelo`
  → `Existe un parte de vuelo con el mismo piloto, anterior a la fecha indicada, en estado Prevuelo. ...`
- solapamiento horario con partes en `postvuelo`/`cerrado` del mismo día compartiendo
  tripulante → `... (SOLAPAMIENTO)`
- el piloto (o supervisor) no puede ser profesor de un parte de escuela cerrado solapado
  → `El piloto o el piloto supervisor esta de profesor en un parte de escuela para la fecha y hora indicada. Parte de escuela: {id}`

**7. `ComprobacionParteEscuelaHandler`** (solo si hay sílabus)
Coherencia VTS / SPIC / doble mando:
- todos los sílabus del parte deben ser del mismo tipo
  → `VUELO VTS: Todos los silabus deben ser VTS o VBS o NBS.\nVUELO SPIC: ...\nVUELO DOBLE MANDO: ...`
- **VTS**: `piloto_id == alumno.piloto_id` → si no, `VUELO VTS: El piloto y el alumno deben ser el mismo.`
  y exige `piloto_supervisor_id` → `VUELO VTS: Debe tener un profesor supervisor.`
- **SPIC**: exige `piloto_id` y `verificado`, y prohíbe `operador`, `piloto_supervisor_id`, `alumno`
  → `VUELO SPIC: En el parte de vuelo debe tener un piloto(Instructor) y un verificado(Alumno).`
  y `piloto_id != verificado` → `VUELO SPIC: El piloto y el verificado deben ser diferentes.`
- **Doble mando**: exige `piloto_id` y `alumno`, prohíbe `operador`, `piloto_supervisor_id`, `verificado`
  → `VUELO DOBLE MANDO: En el parte de vuelo debe tener un piloto(Instructor) y un Alumno(Alumno).`
  y `piloto_id != alumno.piloto_id` → `VUELO DOBLE MANDO: El piloto y el alumno deben ser diferentes.`

**8. `ComprobacionDatosGeneralesHandler`**

| Condición de fallo | Mensaje |
|---|---|
| `distanciatotalprevista == 0` | `Distancia total prevista no válida ` |
| `numtripulacion == 0` | `Número de personas tripulación no válido ` |
| `tiempoprevisto > 3.0` | `El valor del tiempo previsto de vuelo no puede ser superior a 3 horas` |
| `not notam_revisado` | `Este vuelo no puede pasar a postvuelo. NO HA REVISADO NOTAM` |
| `meteo is False` | `Es necesario especificar la información meteorológica` |
| `horasalida <= 0` | `Hora de salida no válida` |
| `tacomsalida <= 0` y tipo != `EC120B` | `Valor tacómetro de salida no válido` |
| `oilqty < 0` | `Es obligatorio indicar la cantidad de aceite añadida. 0 es un valor válido.` |
| `helicoptero_id.horas_remanente <= tiempoprevisto` | `El tiempo de vuelo previsto (HH:MM) excede el número de horas disponibles (HH:MM) para esta máquina` |
| alguno de los 4 `valid_*cg` es `False` | `El peso y centrado no es correcto.` |
| `not performance` | `No hay Performance.` |
| `pasajeros_wb != numtripulacion + numpax + numpae` | `La suma de tripulantes, (pax /AESA) y (AL/PA/PE/PAE/PO) no es igual al numero de pesos introducidos en la Carga y Centrado.` |
| `ruta_id.water_zone` y `not flotadores` | `La ruta establecida tiene areas autorotativas sobre el agua, marca el check de Flotadores.` |
| `not vuelo_tipo_line` | `No hay comentario logbook` |

**9. `ComprobacionDatosCombustibleHandler`**

| Condición de fallo | Mensaje |
|---|---|
| `consumomedio_vuelo == 0` | `El valor del consumo medio esta a 0, revisa el parte de vuelo.` |
| `combustiblelanding <= 0` | `Combustible previsto aterrizaje no válido` |
| `fuelsalida < combustibleminimo` | `Cantidad combustible salida es inferior al combustible mínimo` |
| `fuelsalida > 170` y tipo `CABRI G2` | `Valor combustible al despegue excede el límite máximo` |
| `fuelsalida > 110` y tipo `R22` | ídem |
| `fuelsalida > 180` y tipo `R44` | ídem |
| `fuelsalida > 410` y tipo `EC120B` | ídem |

**10. `ComprobacionPerfilesFormacionHandler`**
Comprueba que el alumno equivalente al piloto (o al supervisor, si `not supervisor_privados`)
tiene un perfil de formación activo para el tipo de helicóptero y el tipo de vuelo, sin
cursos ni acciones con semáforo rojo. Igual para el operador.
Mensajes:
- `{nombre} tiene el curso "{descripcion}" del perfil de formación "{pf}" con el semáforo en rojo desde el {fecha}`
- `{nombre} tiene la acción "{accion}" del perfil de formación "{pf}" con el semáforo en rojo desde el {fecha}`
- `{nombre} no tiene el perfil de formación para la operación y el tipo de aeronave del parte de vuelo`

### 7.2 Cadena POSTVUELO → CERRADO (`wkf_act_cerrado`)

`initChainToCerrado` (`leulit_vuelo.py:142`), handlers en
`addons/leulit_operaciones/vuelo_chain_cerrado.py`. Orden **realmente ejecutado**:

**1. `ComprobacionPresupuestoHandler`** — `presupuesto_vuelo` obligatorio
→ `Este vuelo no puede pasar a cerrado. NO HA SELECCIONADO EL PRESUPUESTO`

**2. `ComprobacionChecksHandler`** — `checklist_postvuelo_realizado` obligatorio
→ `Este vuelo no puede pasar a cerrado. NO HA MARCADO EL DEBRIEFING CON LOS TRIPULANTES/ INSPECCIÓN POSTVUELO CÓMO REALIZADA`

**3. `ComprobacionUsuarioPilotoHandler`** — igual que en la cadena de postvuelo.

**4. `ComprobacionHelicopteroHandler`** — no en taller, sin anomalía sin firmar.

**5. `ComprobacionDescansoHandler`** — respeta el descanso del piloto entre vuelos del
mismo día. Mensajes:
- `Se debe respetar el descanso de los Pilotos. Total tiempo de vuelo: {total}`
- `Se debe respetar el descanso de los Pilotos. Hora llega vuelo anterior: {h}, Descanso requerido: {d}, Hora siguiente vuelo: {hs}`
  (el descanso requerido es `round(total_tiempo_vuelo * 20 / 60, 2)` horas)

**6. `ComprobacionDatosGeneralesHandler`**

| Condición de fallo | Mensaje |
|---|---|
| `airtime < 0` | `Valor Air Time no válido` |
| `airtime > tiemposervicio` | `Valor Air Time no puede ser mayor o igual que el tiempo de servicio` |
| `tiemposervicio > 3.0` | `El valor del tiempo previsto de vuelo no puede ser superior a 3 horas` |
| `uso_gancho > tiemposervicio` | `El tiempo de uso del gancho no puede ser superior al tiempo del servicio realizado.` |
| tipo != `EC120B` y `tacomllegada <= 0` | `Valor tacómetro de llegada no válido` |
| tipo != `EC120B` y `tacomllegada <= tacomsalida` | `Valor tacómetro de llegada debe ser superior al de salida` |
| tipo == `EC120B` y `ngvuelo <= 0` | `Valor NG no válido` |
| tipo == `EC120B` y `nfvuelo <= 0` | `Valor NF no válido` |
| `helicoptero_id.horas_remanente < airtime` | `El tiempo de vuelo previsto (HH:MM) excede el número de horas disponibles (HH:MM) para esta máquina` |

**7. `ComprobacionParteEscuelaHandler`** — si hay alumno/verificado y no hay sílabus
→ `No se han introducido la información del Silabus`; si hay sílabus exige
`comentario_escuela` y `valoracion_escuela` → `Se tiene que rellenar el comentario y la valoración en el parte de vuelo`.
Después **crea el `leulit.parte_escuela`** y valida cada sílabus:
- sílabus TEST sin adjuntos → `Este Parte contiene un Silabus TEST que debe contener archivos adjuntos obligatorios.`
- sílabus TEST con `nota == -1` → `Este Parte contiene un Silabus TEST que debe contener nota obligatoria.`
- sílabus con valoración vacía → `Este Parte contiene una valoración en el Silabus que debe tener un valor obligatorio.`
- sílabus nocturno con `nightlandings == 0` → `Este Parte contiene un Silabus con actividad nocturna que debe tener registrado aterrizajes nocturnos.`

**8. `UpdateProximoVueloHandler`** — propaga `tacomllegada` → `tacomsalida` y
`fuelllegada` → `editfuelrem` al siguiente parte en prevuelo del mismo helicóptero.

> ⚠️ **`ComprobacionDatosCombustibleHandler` de la cadena de cerrado NO se ejecuta.**
> En `initChainToCerrado` (`leulit_vuelo.py:150-151`) la variable `chain7` se asigna dos
> veces y `ComprobacionDatosCombustibleHandler` queda descolgada de la cadena. También
> queda fuera `ComprobacionOverlapPartesEscuelaVueloHandler`. Es un bug del ERP, **no lo
> reproduzcáis "corrigiéndolo"**: si la app validase en cliente
> `fuelllegada > 0` o `fuelsalida > fuelllegada` estaría siendo más estricta que el ERP y
> bloquearía cierres que hoy funcionan. Ver §12.

### 7.3 Validaciones que sí saltan al guardar (`@api.constrains`)

| Restricción | Condición | Mensaje |
|---|---|---|
| `_check_airtime_multiple_of_6_minutes` | `round(airtime*60) % 6 != 0` | `El Airtime debe ser múltiplo de 6 minutos.` |
| `_check_ng_nf` | `ngvuelo > 4` | `El NG del vuelo no puede ser mayor de 4.` |
| `_check_ng_nf` | `nfvuelo > 4` | `El NF del vuelo no puede ser mayor de 4.` |

**El airtime solo admite múltiplos de 0.1 h (6 min).** El selector de airtime debe ser un
control con paso de 6 minutos, no un campo libre.

### 7.4 Validación adicional al firmar el cierre — actividad aérea

`firmar_doc_parte_vuelo` (`addons/leulit_esignature/vuelo.py:414`), cuando
`estado == 'postvuelo'`: tras pasar la cadena, llama a `verificar_actividad_aerea(fecha, partner)`
para `piloto_id`, `operador`, `alumno` y `verificado`. Si alguno excede el tiempo máximo de
actividad aérea del día:

→ `No se puede firmar el parte de vuelo porque se ha excedido el tiempo máximo de actividad aérea. Debe crear una ocurrencia para gestionar el exceso de tiempo de actividad aérea.`

### 7.5 Caso especial: piloto freelance

Al firmar un **prevuelo**, si el usuario es piloto freelance
(`res.users.get_piloto_freelance()`) y no tiene registro en
`leulit.freelance_actividad_aerea` para `fechavuelo`, `firmar_doc_parte_vuelo` **devuelve
una acción** que abre el wizard `leulit.wizard_freelance_actividad_aerea` con
`default_date = fechavuelo`, y **no** ejecuta la cadena.

La app debe detectar que la respuesta del botón es un `ir.actions.act_window` sobre
`leulit.wizard_freelance_actividad_aerea` y presentar la pantalla equivalente.

---

## 8. Flujo de firma electrónica (OTP)

### 8.1 Secuencia

```
 App                                Odoo
  │                                   │
  │ 1. call_kw leulit.vuelo           │
  │    .firmar_doc_parte_vuelo([id])  │
  ├──────────────────────────────────►│  ejecuta la cadena de validación (§7)
  │                                   │  si falla → UserError (mostrar y abortar)
  │                                   │  si OK → write control_firma='pendiente'
  │◄──────────────────────────────────┤  (o devuelve act_window si freelance, §7.5)
  │                                   │
  │ 2. call_kw leulit_signaturedoc    │
  │    .codeFromServer([])            │
  ├──────────────────────────────────►│  notp = res.users.get_otp()   (TOTP, período 20 s)
  │◄──────────────────────────────────┤  {'notp': '482913'}
  │                                   │
  │ 3. el usuario teclea/confirma OTP │
  │                                   │
  │ 4. call_kw leulit_signaturedoc    │
  │    .checksignatureRef([])         │
  │    context: {'args': {            │
  │       'otp':  <tecleado>,         │
  │       'notp': <de codeFromServer>,│
  │       'modelo': 'leulit.vuelo',   │
  │       'idmodelo': <id>}}          │
  ├──────────────────────────────────►│  si otp == notp:
  │                                   │     vuelo.buildPdfSigned(...)
  │                                   │        prevuelo  → estado='postvuelo', control_firma='no-firmado'
  │                                   │        postvuelo → estado='cerrado',   control_firma='firmado'
  │                                   │     genera los PDF firmados (POV, PTV, F27)
  │◄──────────────────────────────────┤  {'valid': true|false, 'error': ..., 'errmsg': ...}
  │                                   │
  │ 5. recargar el registro           │
```

### 8.2 Detalles del OTP

- Generado con `pyotp.TOTP(secret, interval=60)` con `period` forzado a **20 segundos**
  (`addons/leulit_esignature/ResUsers.py:35`). El secreto es por usuario (`res.users.otp_secret`).
- `checksignatureRef` **solo compara `otp == notp`** del contexto. No verifica el TOTP
  contra el reloj. Es decir, la seguridad efectiva reside en que `notp` viene del servidor.
- **Decisión tomada (2026-08-18): se mantiene el comportamiento actual del ERP.** La app
  muestra el código devuelto por `codeFromServer()` y **el piloto lo teclea** en un campo
  aparte. La app envía como `otp` lo que el piloto ha escrito y como `notp` lo que devolvió
  el servidor; si no coinciden, `checksignatureRef` devuelve `valid: false` y el parte no
  avanza de estado.
- **No implementar** firma de un toque (`otp = notp` automático) ni biometría: el parte de
  vuelo firmado es documento aeronáutico y el gesto deliberado de teclear forma parte del
  procedimiento vigente.
- Consecuencia de diseño: el campo de entrada del OTP **no debe autocompletarse** con el
  código mostrado, ni permitir copiar y pegar desde él. Si se autocompletase, la app estaría
  implementando de hecho la opción descartada.

### 8.3 Quién puede firmar

`uidCanSign` (`addons/leulit_esignature/SignatureDoc.py:117`): para `leulit.vuelo` solo el
`res.users` asociado al `partner_id` del `piloto_id` **o** del `piloto_supervisor_id`.

### 8.4 Bandeja de pendientes de firma

`leulit_signaturedoc.getAllPendientesFirma()` sobre `leulit.vuelo` devuelve los partes con
`control_firma='pendiente'`, `estado in ('prevuelo','postvuelo')` y `fechavuelo > 2022-02-22`,
ordenados por fecha descendente. `leulit_signaturedoc.allPendienteFirmaOdoo()` devuelve la
lista consolidada de todos los modelos firmables. Útil para una pantalla "Pendientes de firma".

---

## 9. Weight & Balance (`leulit.weight_and_balance`)

Es un submodelo con **~90 grupos de campos**, cada uno con 5 columnas:
`X`, `X_long_arm`, `X_lat_arm`, `X_long_moment`, `X_lat_moment`, y en muchos casos un
booleano `X_cb` que indica si el elemento se contabiliza.

### 9.1 Apertura desde el parte — `wizard_add_wb`

`leulit_vuelo.py:1007`. Busca (o crea) el W&B del vuelo y **prepara un contexto de defaults**:

| Clave de contexto | Valor |
|---|---|
| `default_vuelo_id` | `id` del vuelo |
| `default_helicoptero_id` | `helicoptero_id.id` |
| `default_helicoptero_tipo` | `helicoptero_tipo` |
| `default_helicoptero_modelo` | `helicoptero_id.modelo.name` |
| `default_fueltakeoff` | `fuelsalida_kg` |
| `default_fuellanding` | `combustiblelanding_kg` |
| `default_frs` | peso del asiento delantero derecho |
| `default_fls` | peso del asiento delantero izquierdo |
| `default_cyclic_cb`, `default_pedals_cb`, `default_collective_cb`, `default_dualcontrols_cb` | mandos duales presentes/retirados |

Reglas de asignación de pesos de asiento:
```
frs = peso_piloto ; fls = 0
si operador:              fls = operador.peso_piloto
si alumno y piloto_id:    frs = alumno.peso_piloto
                          fls = peso_piloto  si alumno.partner_id != piloto_id.partner_id, si no 0
si verificado:            frs = verificado.peso_piloto ; fls = peso_piloto
```
Mandos duales (solo si **no** hay alumno ni verificado):
```
R22            → cyclic_cb = pedals_cb = collective_cb = True
R44 / EC120B   → dualcontrols_cb = True
```

Si ya existía un W&B y el vuelo está en `prevuelo`/`postvuelo` y ha cambiado el tipo de
helicóptero, `fuelsalida_kg` o `combustiblelanding_kg`, se llama a `change_data_vuelo()` +
`updateTotals()` para regenerar brazos y momentos.

### 9.2 Campos por tipo de helicóptero

`_get_fields_list(tipohelicoptero)` (`leulit_weight_and_balance.py:57`) devuelve la lista
de campos activos para `R22`, `R44`, `EC120B` y `CABRI G2`. **La app debe leer
`fieldslist` del registro** (campo `Char` calculado que contiene esa lista serializada)
en lugar de duplicar la tabla; así los cambios en el ERP no rompen la app.

Los brazos por defecto los fija `_set_data_r44` / `_set_data_r22` / `_set_data_rEC120B` /
`_set_data_cabriG2` en el `default_get`, y luego viven en el registro. La app solo edita
los pesos (`X`) y los booleanos (`X_cb`).

### 9.3 Cálculo de totales (`updateTotals`, `leulit_weight_and_balance.py:413`)

```
para cada key en fieldslist:
    contar = getattr(key + '_cb')  si existe ese campo, si no True
    si contar:
        key_long_moment = key * key_long_arm
        key_lat_moment  = key * key_lat_arm
        total           += key
        total_longmoment += key_long_moment
        total_latmoment  += key_lat_moment
    si no:
        key_long_moment = key_lat_moment = 0

takeoff_gw             = total - fuellanding
takeoff_gw_long_moment = total_longmoment - fuellanding_long_moment
takeoff_gw_lat_moment  = total_latmoment  - fuellanding_lat_moment
takeoff_gw_long_arm    = takeoff_gw_long_moment / takeoff_gw   (0 si takeoff_gw <= 0)
takeoff_gw_lat_arm     = takeoff_gw_lat_moment  / takeoff_gw   (0 si takeoff_gw <= 0)

landing_gw             = total - fueltakeoff
landing_gw_long_moment = total_longmoment - fueltakeoff_long_moment
landing_gw_lat_moment  = total_latmoment  - fueltakeoff_lat_moment
landing_gw_long_arm    = landing_gw_long_moment / landing_gw   (0 si landing_gw <= 0)
landing_gw_lat_arm     = landing_gw_lat_moment  / landing_gw   (0 si landing_gw <= 0)

maswithoutfuel             = total - fuellanding - fueltakeoff
maswithoutfuel_long_moment = total_longmoment - fuellanding_long_moment - fueltakeoff_long_moment
maswithoutfuel_lat_moment  = total_latmoment  - fuellanding_lat_moment  - fueltakeoff_lat_moment
maswithoutfuel_long_arm    = maswithoutfuel_long_moment / maswithoutfuel  (0 si <= 0)
maswithoutfuel_lat_arm     = maswithoutfuel_lat_moment  / maswithoutfuel  (0 si <= 0)
```

> Nota: `takeoff_gw` resta `fuellanding` y `landing_gw` resta `fueltakeoff`. Está así en el
> código de producción; reprodúzcase literalmente.

### 9.4 Validación del centro de gravedad (envolventes)

**En el ERP web esto lo hace JavaScript** (`addons/leulit_operaciones/static/src/js/weight_and_balance.js`)
y el resultado se escribe en los cuatro booleanos `valid_{takeoff|landing}_{long|lat}cg`.
**La app móvil debe replicarlo**, porque sin esos booleanos el parte no pasa a postvuelo.

Algoritmo:
```
punto_takeoff_long = { x: takeoff_gw_long_arm, y: takeoff_gw }
punto_takeoff_lat  = { x: takeoff_gw_lat_arm,  y: takeoff_gw }
punto_landing_long = { x: landing_gw_long_arm, y: landing_gw }
punto_landing_lat  = { x: landing_gw_lat_arm,  y: landing_gw }

valid_takeoff_longcg = pointInPoly(punto_takeoff_long, Polygons[modelo].long)
valid_takeoff_latcg  = pointInPoly(punto_takeoff_lat,  Polygons[modelo].lat)
valid_landing_longcg = pointInPoly(punto_landing_long, Polygons[modelo].long)
valid_landing_latcg  = pointInPoly(punto_landing_lat,  Polygons[modelo].lat)
```

`pointInPoly` es el algoritmo clásico de ray casting (crossing number):
```javascript
function pointInPoly(pt, poly) {
    let c = false;
    for (let i = -1, l = poly.length, j = l - 1; ++i < l; j = i) {
        const cond = ((poly[i].y <= pt.y && pt.y < poly[j].y) || (poly[j].y <= pt.y && pt.y < poly[i].y))
          && (pt.x < (poly[j].x - poly[i].x) * (pt.y - poly[i].y) / (poly[j].y - poly[i].y) + poly[i].x);
        if (cond) c = !c;
    }
    return c;
}
```

**Envolventes (`y` = peso en kg, `x` = brazo en cm)** — copiar tal cual:

```
R22            long: (417,242.6) (417,259.08) (532.9,259.08) (621.4,254.0) (621.4,245.1) (578.33,242.6)
               lat:  (-5.58,246.38) (-5.58,248.92) (-1.27,259.08) (3.04,259.08) (6.6,248.92) (2.54,242.57) (-2.32,242.57)

R44 / R44 Raven I / R44 Clipper I / R44 Astro
               long: (703,233.68) (703,260.0) (907,260.0) (1089,248.92) (1089,236.22) (998,233.68)
               lat:  (-7.62,233.68) (-7.62,254.0) (-4.0,260.0) (4.0,260.0) (7.62,254.0) (7.62,233.68)

R44 Raven II / R44 Clipper II
               long: (703,233.68) (703,260.0) (907,260.0) (1134,248.92) (1134,236.22) (998,233.68)
               lat:  igual que R44

EC120B         long: (1035,404.75) (1035,416.0) (1300,415.0) (1715,409.5) (1715,388.0) (1400,383.0) (1300,383.0)
               lat:  (-9.0,400.0) (-9.0,416.0) (8,416.0) (8,400.0) (4.8,387.4) (4.8,383.0) (-5.1,383.0) (-5.1,387.4)

EC-HIL (matrícula concreta, no modelo)
               long: (1035,404.75) (1035,416.0) (1300,415.0) (1800,409.5) (1800,388.0) (1400,383.0) (1300,383.0)
               lat:  igual que EC120B

CABRI G2       long: (470,212.0) (500,212.0) (700,202.5) (700,191.5) (550,191.5)
               lat:  (-80,211.5) (80,211.5) (80,191.0) (-80,191.0)
```
*(pares expresados como `(y, x)`, tal y como aparecen en el fichero fuente)*

La clave del diccionario es `helicoptero_modelo` (`R44 Raven II`, ...) salvo `EC-HIL`, que
es la **matrícula** (`helicoptero_id.name`) y tiene envolvente propia ampliada.

### 9.5 Guardado — `btn_save_wizard`

`leulit_weight_and_balance.py:17`:
1. `_recalculate_and_save_totals()` (persiste los totales; `onchange` por sí solo no guarda).
2. `vuelo_id.weight_and_balance_id = id`.
3. Si `fueltakeoff < 0` → pone los 4 `valid_*` a `False` y lanza
   `El valor indicado en el campo combustible al despegue no es correcto`.
4. Si `fuellanding < 0` → ídem con
   `El valor indicado en el campo combustible previsto al aterrizaje no es correcto`.
5. Calcula `pasajeros_wb` en el vuelo = número de asientos con peso > 0 entre
   `frs`, `fls`, `aftrp`, `aftlp`, `aftcp`.
6. Devuelve `{'type': 'ir.actions.act_window_close'}`.

> **`pasajeros_wb` es la fuente del error "La suma de tripulantes... no es igual al número de
> pesos introducidos en la Carga y Centrado"** (§7.1-8). La UI debe mostrar, junto al W&B,
> el contador `pasajeros_wb` vs `numtripulacion + numpax + numpae` para que el piloto vea
> el desajuste antes de firmar.

---

## 10. Performance (`leulit.performance`)

**Decisión tomada (2026-08-18): las entradas del usuario son solo `peso` y `temperatura`,
pero el gráfico IGE/OGE hay que generarlo y guardarlo.** La app replica el renderizado que
hoy hace JavaScript en el navegador.

### 10.1 El modelo

`addons/leulit_operaciones/models/leulit_performance.py`:

| Campo | Tipo | Origen |
|---|---|---|
| `vuelo` | m2o `leulit.vuelo` | lo fija el servidor |
| `peso` | float (kg) | **solo lectura**: `takeoff_gw` del W&B del vuelo |
| `temperatura` | float (ºC) | **único campo que teclea el usuario** |
| `ige` | binary | PNG del gráfico *In Ground Effect* generado por la app |
| `oge` | binary | PNG del gráfico *Out of Ground Effect* generado por la app |

El formulario del ERP (`leulit_performance.xml`) muestra `peso` readonly, `temperatura`
editable, un botón "Calcular" (`dummy_calcular`, que no hace nada en servidor: el cálculo es
íntegramente de cliente) y las dos gráficas lado a lado bajo los títulos
`IN GROUND EFFECT` y `OUT GROUND EFFECT`.

### 10.2 Apertura desde el parte — `button_performance_vuelo`

`leulit_vuelo.py:1089`:
1. `peso = takeoff_gw` del último W&B del vuelo (consulta SQL directa; 0 si no hay W&B).
2. Elige la vista según `helicoptero_modelo`, y con ella el par de gráficas.
3. Si el modelo no está contemplado lanza
   `NO SE PUEDE CALCULAR PERFORMANCE PARA ESTE MODELO PORQUE NO HA SIDO IMPLEMENTADO EN EL SISTEMA`
4. Si ya existía Performance lo reescribe con `{'peso': peso, 'ige': None, 'oge': None}`
   (**borra las imágenes**: hay que regenerarlas); si no, crea
   `{'peso': peso, 'vuelo': id, 'temperatura': 0}`.

### 10.3 Qué gráfica corresponde a cada modelo

| `helicoptero_modelo` | Vista del ERP | Gráfica IGE | Gráfica OGE |
|---|---|---|---|
| `EC120B` | `leulit_performance_EC120B_form` | `ec_in` | `ec_out` |
| `EC120B` con matrícula `EC-HIL` **y** `weight_and_balance_id.gancho_carga_cb` | `leulit_performance_ECHIL_form` | `hil_in` | `hil_out` |
| `R22 Beta` | `leulit_performance_R22_form` | `r22_in` | `r22_out` |
| `R22 Beta II` | `leulit_performance_R22_2_form` | `r22_2_in` | `r22_2_out` |
| `R44 Astro`, `R44 Raven I`, `R44 Clipper I` | `leulit_performance_R44_form` | `r44_in` | `r44_out` |
| `R44 Raven II`, `R44 Clipper II` | `leulit_performance_R44_2_form` | `r44_2_in` | `r44_2_out` |
| `CABRI G2` | `leulit_performance_CABRI_G2_form` | `cabri_in` | `cabri_out` |

Cualquier otro modelo (`AS350`, `EC130`, `DJI`, ...) **no tiene performance implementado**:
la app debe mostrar el mismo `UserError` que el ERP y no ofrecer el botón.

### 10.4 Imágenes de fondo

Están en `addons/leulit_operaciones/static/src/img/`. Hay que **copiarlas como assets de la
app** (no descargarlas del servidor: son estáticas y la app las necesita para pintar).

| Gráfica | Fichero | Tamaño real del fichero | Tamaño del canvas |
|---|---|---|---|
| `ec_in`, `hil_in` | `ec_120_b_in.png` | 481 × 636 | 500 × 725 |
| `ec_out`, `hil_out` | `ec_120_b_out.png` | 485 × 645 | 520 × 770 |
| `r22_in` | `r22_beta_in.png` | 495 × 720 | 500 × 725 |
| `r22_out` | `r22_beta_out.png` | 520 × 770 | 520 × 770 |
| `r22_2_in` | `r22_beta_2_in.png` | 500 × 717 | 500 × 717 |
| `r22_2_out` | `r22_beta_2_out.png` | 500 × 790 | 500 × 790 |
| `r44_in` | `R44_IGE_HOVER_CEILING_VS_GROSS_WEIGHT.png` | 620 × 900 | 620 × 900 |
| `r44_out` | `R44_OGE_HOVER_CEILING_VS_GROSS_WEIGHT.png` | 620 × 900 | 620 × 900 |
| `r44_2_in` | `R44_2_IGE_HOVER_CEILING_VS_GROSS_WEIGHT.jpg` | 403 × 620 | 500 × 725 |
| `r44_2_out` | `R44_2_OGE_HOVER_CEILING_VD_GROSS_WEIGHT.jpg` | 438 × 745 | 520 × 770 |
| `cabri_in` | `cabri_g2_in.png` | 470 × 515 | 500 × 725 |
| `cabri_out` | `cabri_g2_out.png` | 465 × 515 | 520 × 770 |

> El canvas es en varios casos **mayor** que la imagen: el ERP dibuja la imagen en (0,0) y
> deja el resto en blanco. Reprodúzcase igual, porque el punto se posiciona respecto al
> origen de la imagen, no al del canvas.
>
> `hil_hook_out.png` existe en la carpeta pero **no se usa**: la gráfica de EC-HIL apunta a
> `ec_120_b_out.png` (`src_hil_out` en el fichero de constantes). No es un error de esta
> documentación, está así en el addon.

### 10.5 Constantes de calibración

Cada gráfica tiene siete parámetros de calibración y un juego de curvas de temperatura
(entre 6 y 10 curvas según modelo), todas expresadas en píxeles de la imagen de fondo.

Para evitar errores de transcripción, **están ya portadas a Dart** en
`docs/superpowers/specs/assets/performance_constants.dart` (generado automáticamente desde
`addons/leulit_operaciones/static/src/js/performance_constants.js`). Ese fichero define:

```dart
class PerfCurve { final double temp; final List<List<double>> pts; }   // pts = [[x,y], ...] ordenados por x
class PerfChart {
  final String asset;
  final int canvasWidth, canvasHeight;
  final double inicioEje;      // origen del eje de peso, EN LIBRAS
  final double proporcion;     // pixeles por libra
  final double alturaImagen;   // alto usado para trasladar el origen
  final double inicioEjeX, inicioEjeY;
  final List<PerfCurve> temperaturas;
}
const Map<String, PerfChart> perfCharts;                        // clave: 'ec_in', 'r22_out', ...
const Map<String, ({String ige, String oge})> perfChartPorModelo;
```

Si las curvas cambian en el addon, hay que regenerar ese fichero.

### 10.6 Algoritmo de cálculo

`addons/leulit_operaciones/static/src/js/performance.js`. Dos pasos y un dibujo.

**Paso 1 — coordenada X a partir del peso:**
```
// El peso llega en kg desde el W&B, pero los ejes están calibrados en libras.
// pasarLibras es SIEMPRE true en las siete gráficas.
x = (peso_kg * 2.2046227 - inicioEje) * proporcion
```

**Paso 2 — coordenada Y a partir de la temperatura y de x:**
```
calcAltura(curvas, temperatura, x):
    bandas = curvas ordenadas por temp ascendente
    si no hay bandas          -> 0
    si solo hay una           -> interpAtX(banda[0].pts, x)
    si temperatura <= temp[0] -> interpAtX(banda[0].pts, x)          # sin extrapolar en temperatura
    si temperatura >= temp[n-1] -> interpAtX(banda[n-1].pts, x)
    si no, localizar i tal que temp[i] <= temperatura < temp[i+1]:
        y1    = interpAtX(banda[i].pts,   x)
        y2    = interpAtX(banda[i+1].pts, x)
        ratio = (temperatura - temp[i]) / (temp[i+1] - temp[i])
        -> y1 + ratio * (y2 - y1)
```

`interpAtX` es interpolación lineal en X sobre los puntos de una curva, **con extrapolación
lineal** por ambos extremos usando el primer/último segmento:
```
interpAtX(pts, x):
    si len(pts) == 1              -> pts[0].y
    si x <= pts[0].x              -> extrapolar con el segmento (pts[0], pts[1])
    si x >= pts[n-1].x            -> extrapolar con el segmento (pts[n-2], pts[n-1])
    si no, buscar el segmento que contiene x e interpolar linealmente
    (si el segmento tiene dx == 0, devolver la y del extremo)
```

**Paso 3 — pintar el punto:**
```
originX = inicioEjeX
originY = inicioEjeY + alturaImagen
puntoX  = originX + x
puntoY  = originY + y
```
Círculo de **radio 6**, relleno `#FF0000`, borde `#FFFFFF` de **2 px**, sobre la imagen de
fondo ya dibujada en (0,0).

> `inicioEjeY` es negativo en todas las gráficas (por ejemplo `-185 = 535 - 720` en `r22_in`)
> y `y` también lo es, de modo que el punto queda por encima del origen. Es la traslación de
> coordenadas del canvas original; copiarla literalmente.

### 10.7 Guardado — cómo se persisten `ige` y `oge`

El ERP hace `canvas.toDataURL("image/png")` y escribe **la cadena completa** en el campo
binario. Verificado en producción (registro `leulit.performance` id 13783): el valor
almacenado empieza por

```
data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAfQAAALNCAYAAADZS5Ny...
```

es decir, **con el prefijo `data:image/png;base64,` incluido**, que no es base64 válido.

**La app debe escribir exactamente el mismo formato** (`'data:image/png;base64,' + base64(png)`)
para que los registros nuevos sean indistinguibles de los actuales y los visores que ya
existen sigan funcionando. No "arreglarlo" guardando base64 limpio: rompería la coherencia
con los ~13.000 registros históricos.

Ambas imágenes se generan siempre a la vez, con el tamaño de canvas de la tabla de §10.4.

### 10.8 Secuencia completa desde la app

```
1. Botón "Performance" en la pantalla Prevuelo 2
2. call_kw leulit.vuelo.button_performance_vuelo([id])
      -> UserError si el modelo no está implementado
      -> ActWindow sobre leulit.performance con res_id
3. web_read del registro: peso (readonly), temperatura
4. El usuario teclea la temperatura
5. La app calcula x e y para IGE y OGE, y pinta ambos gráficos
6. Al guardar:
      write leulit.performance {
        temperatura: <valor>,
        ige: 'data:image/png;base64,' + <png IGE>,
        oge: 'data:image/png;base64,' + <png OGE>,
      }
7. Volver al parte. La validación de postvuelo solo exige que el registro exista
   (`not performance` -> "No hay Performance."), pero el gráfico se adjunta al PDF.
```

## 11. Integración JSON-RPC con Odoo 17

### 11.1 Autenticación

```http
POST https://erp.helipistas.com/web/session/authenticate
Content-Type: application/json

{"jsonrpc":"2.0","method":"call","params":{
  "db":"<nombre_bd>","login":"<usuario>","password":"<contraseña>"}}
```
Respuesta: `result.uid`, `result.user_context`, `result.company_id`, y **cookie `session_id`**
que debe conservarse (`CookieJar`) y enviarse en todas las llamadas siguientes.

Cierre de sesión: `POST /web/session/destroy`.
Comprobación de sesión viva: `POST /web/session/get_session_info`.

### 11.2 Llamada genérica

```http
POST https://erp.helipistas.com/web/dataset/call_kw
Content-Type: application/json

{"jsonrpc":"2.0","method":"call","params":{
  "model":"leulit.vuelo",
  "method":"web_search_read",
  "args":[],
  "kwargs":{ ... }}}
```

### 11.3 Operaciones necesarias

| Caso de uso | Modelo | Método | Notas |
|---|---|---|---|
| Listado de partes | `leulit.vuelo` | `web_search_read` | domain de la acción: `[('fechavuelo','<=', hoy)]`; order `fechavuelo desc, horasalida desc`; specification con los campos del tree (§4) |
| Abrir un parte | `leulit.vuelo` | `web_read` | specification con todos los campos de §4 |
| Crear | `leulit.vuelo` | `web_save` / `create` | **no enviar `codigo` ni `create_uid`** |
| Guardar | `leulit.vuelo` | `web_save` / `write` | enviar también los `force_save` (§4) |
| Recalcular | `leulit.vuelo` | `onchange` | §11.4 |
| Botón | `leulit.vuelo` | `<nombre del método>` | `args: [[id]]`, devuelve `null`, dict de acción, o lanza error |
| Selector m2o | modelo destino | `name_search` | `args: [], kwargs: {name, args: <domain>, operator:'ilike', limit: 20}` |
| Defaults al crear | `leulit.vuelo` | `onchange` con `values={}` o `default_get` | |

Domains a aplicar en los selectores:

| Campo | Domain |
|---|---|
| `helicoptero_id` | `[('baja','=',False)]` |
| `ruta_id` | `[('activo','=',True)]` |
| `presupuesto_vuelo` | `[('flag_flight_part','=',True),('state','=','sale'),('task_done','=',False)]` |
| `alumno` | `[('piloto_id','!=',False)]` |
| `piloto_id`, `verificado`, `piloto_supervisor_id` | sin domain (`leulit.piloto`) |
| `operador` | sin domain (`leulit.operador`) |
| `lugarsalida`, `lugarllegada`, `alternativos` | sin domain (`leulit.helipuerto`) |
| `vuelo_tipo_id` (línea) | sin domain (`leulit.vuelostipo`) |

### 11.4 `onchange` en Odoo 17

```json
{"model":"leulit.vuelo","method":"onchange",
 "args":[
    [<id o vacío si es nuevo>],
    { ...todos los valores actuales del formulario... },
    ["helicoptero_id"],
    { "helicoptero_id": {}, "fuelsalida": {}, "combustibleminimo": {}, ... }
 ],
 "kwargs":{"context":{...}}}
```
- 3.º argumento: lista de campos que han cambiado (vacía = cargar defaults).
- 4.º argumento (`fields_spec`): qué campos quiere recibir de vuelta. **Pedir todos los
  campos del formulario**; los cálculos de combustible tocan una veintena de campos a la vez.

Respuesta: `{"value": {...}, "warning": {"title":..., "message":...}}`.
La app debe aplicar `value` al estado del formulario y mostrar `warning` si viene.

### 11.5 Comandos de campos relacionales (x2many)

| Comando | Significado | Uso aquí |
|---|---|---|
| `(0, 0, {vals})` | crear línea nueva | `vuelo_tipo_line`, `silabus_ids` |
| `(1, id, {vals})` | actualizar línea | `vuelo_tipo_line`, `silabus_ids` |
| `(2, id, 0)` | borrar línea | `vuelo_tipo_line`, `aerovia_ids` |
| `(3, id, 0)` | desvincular | `alternativos` |
| `(4, id, 0)` | vincular | `alternativos` |
| `(6, 0, [ids])` | reemplazar el conjunto | no usar en `alternativos` (es o2m real) |

### 11.6 Errores

Odoo devuelve HTTP 200 con `error` en el cuerpo:
```json
{"error":{"code":200,"message":"Odoo Server Error",
 "data":{"name":"odoo.exceptions.UserError",
         "message":"Este vuelo no puede pasar a postvuelo. NO HA REVISADO NOTAM",
         "arguments":[...], "debug":"..."}}}
```
Mapeo obligatorio:

| `data.name` | Tratamiento en la app |
|---|---|
| `odoo.exceptions.UserError` | Diálogo con `data.message` íntegro. Son mensajes de negocio pensados para el piloto |
| `odoo.exceptions.ValidationError` | Igual, asociado al campo si se puede inferir |
| `odoo.exceptions.AccessError` | "No tiene permisos" + `data.message` |
| `odoo.exceptions.MissingError` | El registro ya no existe → volver a la lista |
| `odoo.http.SessionExpiredException` | Re-login transparente y reintento |
| otros | Error genérico + envío a telemetría con `data.debug` |

### 11.7 Acciones devueltas por los botones

| `type` | Cuándo | Qué hacer |
|---|---|---|
| `ir.actions.act_window` | `wizard_pre_cancelar`, `wizard_add_wb`, `button_performance_vuelo`, freelance | Abrir la pantalla nativa equivalente con `context` y `res_id` |
| `ir.actions.client` con `tag='display_notification'` | `action_obtener_meteo_salida` | Snackbar con `params.title/message/type` |
| `ir.actions.report` | `parte_vuelo_print`, `vuelo_print` | Descargar el PDF por `/report/pdf/<report_name>/<id>` con la sesión activa |
| `ir.actions.act_window_close` | `btn_save_wizard` | Cerrar la pantalla y refrescar el parte |
| `null` | `action_cambiar_pantalla_*`, `fin_act_postvuelo` | Refrescar el registro |

---

## 12. Trampas conocidas — leer antes de implementar

1. **`ComprobacionDatosCombustibleHandler` de la cadena de cerrado no se ejecuta**
   (`leulit_vuelo.py:150-151`, `chain7` asignado dos veces). Tampoco
   `ComprobacionOverlapPartesEscuelaVueloHandler`. **No añadir esas validaciones en cliente.**

2. **`_get_combustible_remanente` escribe en base de datos dentro de un `compute`**
   (`leulit_vuelo.py:1339`): al leer `fuelremanente` se hace `item.write({'editfuelrem': ...})`.
   Consecuencia: leer el registro puede modificarlo. No sorprenderse si `editfuelrem` cambia
   solo tras un `read`.

3. **`onchange helicoptero_id` hace `write()` y `unlink()` reales** (§6.1). En un registro
   nuevo sin guardar esto no aplica, pero al cambiar el helicóptero de un parte existente
   **se borra el Performance sin preguntar**. Avisar al usuario.

4. **`distanciatotalprevista` es readonly y `== 0` bloquea el paso a postvuelo.** Sin ruta
   seleccionada, la única manera de darle valor es editar `tiempoprevisto` (§6.3). Es un
   comportamiento contraintuitivo que hay que reproducir; conviene mostrar la distancia
   calculada de forma prominente para que el piloto detecte si está a 0.

5. **`onchange nv` está invertido**: al marcar "No Volado" se **borran** `nv_uid` y
   `nv_date`; al desmarcarlo se rellenan con el usuario y la fecha actuales
   (`leulit_vuelo.py:2103`). Reprodúzcase literalmente.

6. **`oilqty` default `-1`** y `oilqty_gal` default `-0.26`. El `-1` es el centinela de
   "no informado" (§7.1-8).

7. **`alternativos` es One2many sobre `leulit.helipuerto`**: añadir un alternativo escribe
   `vuelo_id` en el registro maestro del helipuerto. Un helipuerto solo puede ser
   alternativo de un vuelo a la vez. Es una anomalía de modelado del ERP; la app debe
   limitarse a usar `(4,id)`/`(3,id)` y no ofrecer creación.

8. **`_is_last_30_days` está roto** (`leulit_vuelo.py:2168`): hace
   `datetime.strptime(item.fechavuelo, ...)` sobre un objeto `date`, lo que lanza `TypeError`.
   **No usar ese campo ni el filtro asociado.**

9. **No hay reglas de registro (`ir.rule`) sobre `leulit.vuelo`.** El único ACL es
   `Vuelo Access` para el grupo `leulit.RBase` con RWCD completo (id 1181 en producción).
   Cualquier usuario con rol base **ve y puede escribir todos los partes**. Las restricciones
   reales son de negocio (solo el piloto o el supervisor pueden firmar). La app no debe
   asumir que el backend filtra por usuario: si se quiere una vista "mis partes", el domain
   lo pone la app.

10. **`estado_vista` se persiste.** Si dos dispositivos abren el mismo parte, el último
    cambio de pantalla gana. No es un problema funcional, pero explica saltos de pantalla.

11. **Las validaciones no se ejecutan al guardar.** Un parte puede guardarse con datos
    incompletos e inconsistentes; solo revienta al firmar. La app debería mostrar un
    "checklist de firma" con las condiciones de §7 evaluadas en cliente **como ayuda
    visual**, dejando siempre que el servidor sea quien decida.

---

## 13. Modelos relacionados — campos relevantes

### `leulit.helicoptero`
`name` (matrícula), `modelo` (m2o `leulit.modelohelicoptero`), `tipo` (related
`modelo.tipo`), `pesomax`, `velocidad` (KT), `consumomedio` (l/min), `emptyweight`,
`longarm`, `latarm`, `longmoment`, `latmoment`, `statemachine`
(`En servicio`/`En taller`), `horas_remanente`, `strhoras_remanente`, `semaforo`,
`baja`, `airtimestart`, `landingsstart`, `arlandingstart`.

### `leulit.helipuerto`
`name` (indicativo OACI, 4 letras), `descripcion`, `display_name` = `(name) descripcion`,
`municipio`, `tz` (zona horaria, **necesaria para las horas UTC**), `lat`, `long`,
`elevacion`, `hayjeta1`, `hayavgas`, `vuelo_id` (inversa de `alternativos`).

### `leulit.piloto`
`name`, `partner_id` (m2o `res.partner`, requerido), `peso_piloto`, `image_128`,
`profesor`, `state` (`activo`/`baja`), `freelance`, `supervisor_privados`, `n_licencia`.

### `leulit.operador` / `leulit.alumno`
Estructura análoga (`partner_id`, `peso_piloto`, `image_128`). `leulit.alumno` tiene además
`piloto_id`.

### `leulit.vuelostipo`
`name`, `tipo_trabajo` (base de `tipo_actividad`: `AOC`, `NCO`, `ATO`, `LCI`, ...), `privado`.

### `leulit.vuelo_tipo_line`
`vuelo_id`, `vuelo_tipo_id`, `privado`.

### `leulit.rel_planoperacional_aerovia`
`vuelo_id`, `ruta_id`, `aerovia_id`, `aerovia_ruta_id`, `distancia`, `rumbo`,
`altitudprevista`, `altitudseguridad`, `tiempoprevisto`, `strtiempoprevisto`.

### `leulit.rel_parte_escuela_cursos_alumnos` (sílabus)
`rel_vuelo`, `rel_curso`, `rel_silabus`, `rel_parte_escuela`, `rel_docs`, `valoracion`,
`nota`, `sil_test`, `sil_valoracion`, `todo_cerrar`.

### `leulit_signaturedoc`
`name`, `modelo`, `idmodelo`, `referencia`, `esignature`, `hashcode`, `otp`, `otp_qrcode`,
`qrtext`, `estado` (`nuevo`/`validado`/`completado`), `firmado_por`, `fecha_create`,
`fecha_valid`, `attachment_id`, `name_attach`, `firmado`.

---

## 14. Payload real de referencia

Registro `id=18864` (`VUL-0019153`) leído de producción el 2026-08-18:

```json
{
  "id": 18864, "codigo": "VUL-0019153",
  "estado": "prevuelo", "estado_vista": "prevuelo", "control_firma": "no-firmado",
  "fechavuelo": "2026-08-18", "horasalida": 12.0,
  "horallegada": 0.0, "horallegadaprevista": 14.0,
  "tiempoprevisto": 2.0, "tiemposervicio": 0.0, "airtime": 0.0,
  "helicoptero_id": [87, "SE-JXP"], "helicoptero_tipo": "EC120B",
  "piloto_id": [238, "Joan Sampons Ritort"],
  "operador": [251, "Guiu Serra Gavaldà"],
  "alumno": false, "verificado": false, "piloto_supervisor_id": false,
  "lugarsalida": [173, "(Heliport Manresa) Heliport Bombers Manresa"],
  "lugarllegada": [173, "(Heliport Manresa) Heliport Bombers Manresa"],
  "alternativos": [], "ruta_id": false,
  "numtripulacion": 1, "numpax": 0, "numpae": 2, "asiento_pic": "pic_right",
  "reservasfuel": "30", "rodaje": "0", "contingencia": "0", "distancia_alternativo": 0.0,
  "consumomedio_vuelo": 1.92, "editfuelrem": 288.16, "fuelqty": 40.0,
  "fuelsalida": 328.16, "combustibleminimo": 288.0, "combustiblelanding": 97.76,
  "fuelllegada": 0.0, "oilqty": 0.0,
  "tacomsalida": 0.0, "tacomllegada": 0.0,
  "landings": 1, "nightlandings": 0,
  "velocidadprevista": 110.0, "distanciatotalprevista": 220.0,
  "vuelo_tipo_line": [19639],
  "weight_and_balance_id": false,
  "valid_takeoff_longcg": false, "valid_takeoff_latcg": false,
  "valid_landing_longcg": false, "valid_landing_latcg": false,
  "pasajeros_wb": 0,
  "checklist_realizado": true, "checklist_prevuelo_BFF": true,
  "checklist_prevuelo_entre_vuelos": false, "briefing_realizado": true,
  "checklist_postvuelo_realizado": false, "notam_revisado": true,
  "indicativometeo": "lell",
  "presupuesto_vuelo": [1557, "S01557 - HELIPISTAS S.L. MANRESA 5010"],
  "balsa": false, "flotadores": false, "chalecos": false,
  "ifr": false, "nv": false, "comentarios": false
}
```

Comprobación numérica con estos datos (§6.3), tipo `EC120B`:
```
combustibleminimo = 1.92 * (leulit_float_time_to_minutes(2.0 + 0 + 0) + 30)
                  = 1.92 * (120 + 30) = 288.0                      ✓ coincide
fuelsalida        = round(288.16 + 40.0, 2) = 328.16               ✓ coincide
combustiblelanding= 328.16 - (1.92 * 120) = 97.76                  ✓ coincide
horallegadaprevista = 12.0 + 2.0 = 14.0                            ✓ coincide
distanciatotalprevista = 110 kt * 2 h = 220 NM                     ✓ coincide
combustibleminimo_kg = round(288.0 * 0.79, 2) = 227.52
```
Estas cinco igualdades deben ser casos de test en la app.

---

## 15. Vista de lista

### 15.1 Qué partes se muestran — decisión tomada (2026-08-18)

La app **solo muestra los partes propios**, entendiendo por propios aquellos en los que el
usuario conectado es **`piloto_id` o `piloto_supervisor_id`**: los dos roles que pueden
firmar (§8.3). No hay conmutador "ver todos".

Resolución del domain, una sola vez al iniciar sesión:

```
1. partnerId = res.users.read([uid], ['partner_id']).partner_id[0]
2. misPilotoIds = leulit.piloto.search([('partner_id','=', partnerId)])   -> lista de ids
3. domain = ['&',
              ('fechavuelo','<=', hoy),
              '|', ('piloto_id','in', misPilotoIds),
                   ('piloto_supervisor_id','in', misPilotoIds)]
```

Ambos campos apuntan a `leulit.piloto`, así que basta con un único conjunto de ids.

> **No usar el campo `user_vuelo_ids`.** Existe y es buscable
> (`leulit_vuelo.py:1250` y `:1287`), pero (a) incluye también `operador`, `alumno` y
> `verificado`, que es más amplio de lo decidido; (b) hace un `SELECT` de la tabla completa
> —18.539 partes en producción— y devuelve un `id IN (...)` con todos los ids; y (c) ignora
> `operator` y `value`, de modo que `('user_vuelo_ids','=',False)` devuelve el mismo
> conjunto que `=True`. Además, su lado `compute` (`_get_user_vuelo_ids`) está roto: accede
> a `row['id']` sobre una tupla del cursor.

> **Consecuencia asumida:** un usuario que voló como `operador`, `alumno` o `verificado`
> **no verá ese parte en la app**. Es coherente con que la app existe para quien rellena y
> firma el parte, pero conviene saberlo: quien necesite ver el resto sigue teniendo el ERP web.

### 15.2 Distintivo de rol en cada fila

Cada fila indica en qué rol aparece el usuario, porque cambia lo que puede hacer:

| Condición | Distintivo | Significado |
|---|---|---|
| `piloto_id.id ∈ misPilotoIds` | **PIC** | Es el piloto al mando; firma él |
| `piloto_supervisor_id.id ∈ misPilotoIds` y no es PIC | **SUP** | Supervisa; también puede firmar |

Si se cumplen las dos (el usuario es a la vez piloto y supervisor del mismo parte), prevalece
**PIC**. El distintivo se calcula en cliente con `misPilotoIds`, sin llamadas adicionales.

### 15.3 Columnas y decoración (tree 3228)

Orden por defecto `fechavuelo desc, horasalida desc`. Decoración por estado:
`cerrado` verde · `cancelado` rojo · `postvuelo` ámbar · `prevuelo` azul.

Columnas: `semaforo_firma` (widget `semaforo_char`), `codigo`, `helicoptero_id`,
`foto_piloto` (miniatura), `piloto_id`, `presupuesto_vuelo`, `strfechasalida`,
`strfechallegada`, `landings` (suma), `nightlandings` (suma), `tiemposervicio`
(`float_time`, suma), `airtime` (`float_time`, suma), `oilqty` (oculta por defecto),
botón "Resumen" → `action_resumen_parte_de_vuelo`.

`semaforo_firma` (`addons/leulit_esignature/vuelo.py:320`):
```
'N.A.' salvo que estado in ('cerrado','postvuelo') y fechavuelo >= 2022-02-01,
en cuyo caso 'green' si control_firma == 'firmado', si no 'red'
```

---

## 16. Registro de decisiones

| # | Decisión | Impacto |
|---|---|---|
| 1 | ~~Performance: ¿replicar el gráfico?~~ **RESUELTA 2026-08-18: entradas solo peso y temperatura, pero el gráfico se genera y se guarda** (§10) | — |
| 2 | ~~Firma: ¿teclear el OTP o un botón?~~ **RESUELTA 2026-08-18: el piloto teclea el código, como hoy** (§8.2) | — |
| 3 | ~~¿La lista filtra por usuario?~~ **RESUELTA 2026-08-18: solo partes donde el usuario es PIC o supervisor, con distintivo de rol** (§15.1, §15.2) | — |
| 4 | ~~¿Se abre la ficha de anomalías/anotaciones desde la app?~~ **RESUELTA 2026-08-18: solo lectura, filas no pulsables** (§4.1 bloques D y E) | — |

Sin decisiones abiertas a 2026-08-18.
