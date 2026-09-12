# Revisión `leulit_actividad` — Odoo 17.0 Community

Revisión de código estático (sin entorno Odoo disponible). Todas las afirmaciones de "esto falla"
están justificadas leyendo imports, `_inherit`, llamadas y, cuando la duda era sobre la API de
Odoo 17 (`api.Environment.manage`, `self.pool`, `odoo.netsvc`), verificadas contra el código fuente
de Odoo 17 en GitHub (no contra ejecución real).

## 1. Resumen ejecutivo

- **7 críticos**, **7 altos**, **10 medios**, **5 bajos** — 29 hallazgos.
- Lo más grave: una vista SQL que se crea con nombre distinto al que Odoo espera
  (`leulit_actividad_base_rutas.py`), cinco puntos que usan una API de Odoo eliminada hace años
  (`api.Environment.manage()`), un `unlink()` que solo borra el primer registro de un borrado
  múltiple, y una zona horaria mal invertida (`Etc/GMT+2`) que corrompe el cálculo de actividad
  aérea planificada usado para límites de horas de vuelo.
- Varios de los críticos/altos son en la práctica **código muerto hoy** (sin invocador vivo
  detectado por grep en todo el repo) pero están ahí precisamente porque nadie los puede ejecutar
  sin que exploten — riesgo real si se reactivan o se llaman a mano vía shell para un backfill.
- Patrón transversal de mantenibilidad: SQL crudo con `.format()`, `_logger.error()` usado como
  traza de depuración, `threading.Thread` sin manejo de excepciones, y bloques enteros de código
  comentado conviviendo con la implementación activa.

## 2. Tabla de hallazgos

| Severidad | Fichero:línea | Problema | Escenario que lo dispara | Fix propuesto |
|---|---|---|---|---|
| Crítico | `models/leulit_actividad_base_rutas.py:23-24` | `DROP` del nombre correcto de vista, `CREATE VIEW` con nombre distinto (typo) | Cualquier `-u leulit_actividad`; luego cualquier lectura ORM o la SQL cruda de `leulit_actividad_base_dia.py:184-191` sobre fechas < 2021-01-01 | Crear la vista con el nombre de `_table` (`leulit_actividad_base_rutas`) |
| Crítico | `models/leulit_actividad_16bravo.py:87`, `leulit_calendar_event.py:52`, `leulit_actividad_base.py:401`, `leulit_parte_escuela.py:32,216` | `api.Environment.manage()` no existe en Odoo 17 (eliminado ~v10/11) | Cualquier invocación de `upd_datos_scheduled_action`, `run_upd_datos_actividad` (calendar), `data_calculation`, `run_upd_datos_actividad`/`run_recalcular_tiempos_imputados` (parte_escuela) | Sustituir por el patrón correcto ya usado en `leulit_vuelo.py`: `registry(dbname).cursor()` + `api.Environment(new_cr, uid, context)` |
| Crítico | `models/actividad_laboral.py:58` | `intervals.add([...])` — las listas no tienen `.add()` | `SolapamientoHandler.handle()` cuando `abds` (actividades previas del partner/fecha) no está vacío | `intervals.append([...])` |
| Crítico | `models/leulit_parte_escuela.py:146,162` | `item.initChainActividadLaboral()` / `item.initChainActividadAerea()` no existen en `leulit.parte_escuela` (sólo en `leulit.vuelo`/`calendar.event`/`account.analytic.line`) | Cualquier llamada a `updDataActividad`/`updDataActividadFecha` sobre partes de escuela | Definir ambos métodos también en `leulit_parte_escuela.py` (duplicar el patrón de `leulit_vuelo.py`) |
| Crítico | `models/account_analytic_line.py:33-48` | `return super(...).unlink()` dentro del bucle `for item in self:` | Borrado múltiple de `account.analytic.line` desde una vista lista | Sacar el `return` fuera del bucle, iterar sólo para la lógica de `guardia`, llamar `super(AccountAnalyticLine, self).unlink()` una vez |
| Crítico | `models/account_analytic_line.py:51-55` | `self.guardia` sin `ensure_one()` en `write()` | `write()` sobre >1 registro a la vez (edición masiva) | Iterar `for record in self: if record.guardia: record.updDataActividadAerea()` |
| Crítico | `models/leulit_calendar_event.py:82-90` | `pytz.timezone("Etc/GMT+2")`: los nombres `Etc/GMT+N` tienen signo invertido (es UTC-2, no UTC+2) y no aplica DST | Cualquier cálculo de `updDataPlanActividadAerea` (actividad aérea planificada, límites 28d/12m/3m) | Usar `pytz.timezone("Europe/Madrid")`, igual que en `leulit_parte_escuela.py:87` y `account_analytic_line.py:81` |
| Alto | `models/leulit_actividad_aerea.py:143-154` | `_search_user_from_partner` ignora `operator`/`value` y siempre filtra por `self.env.user.partner_id.id` | Cualquier búsqueda `[('user_id','=',X)]` con X distinto del usuario actual | Usar `value`/`operator` reales para construir el dominio de partner |
| Alto | `models/leulit_vuelo.py:142-171`, `leulit_parte_escuela.py:48-78` | `except Exception: ... self.env.cr.rollback()` deshace TODA la transacción del cursor, no sólo la creación fallida; en `leulit_vuelo.py` además `exc` no se usa ni se loguea | Fallo al crear una línea de imputación en medio de una cadena con cambios ya aplicados sin commit | Usar `savepoint()`/cursor propio para el `create`, loguear `exc`/traceback siempre |
| Alto | `models/leulit_actividad_base_dia.py:12-13,46-172` | Global de módulo mutable `_actividades = []`; `readActividades()` la reasigna como variable local (falta `global`) → nunca se actualiza; `updateData()` referencia `item16B`, no definido en ningún sitio | Si se reactiva `updateData`/`getId`/`calcTiempo` (hoy sin invocadores externos) | Eliminar el global compartido entre requests; si se recupera esta ruta, reescribirla sin estado de módulo y corregir `item16B` |
| Alto | `models/leulit_actividad_base_dia.py:175-212` | `tiempo_facturable` es `compute=..., store=True` **sin** `@api.depends` | El campo sólo se calcula al crear el registro; nunca se recalcula cuando cambian las actividades del día | Añadir `@api.depends(...)` con los campos/relaciones de los que depende |
| Alto | `models/leulit_actividad_base_rutas.py` | Sin entrada en `security.xml` (único modelo del addon sin `ir.model.access`) | Cualquier acceso ORM al modelo por un usuario no superuser | Añadir regla de acceso (lectura) además de arreglar el bug crítico de la vista |
| Alto | `models/leulit_checklist.py:39-42` | `if self.freelance_pilot` sin `ensure_one()` en `write()` | `write()` sobre >1 checklist a la vez | Iterar con `for rec in self: ...` antes de decidir si bloquear |
| Medio | `models/account_analytic_line.py:189-218` | `_check_overlap_task` (`@api.constrains`) calcula `isOverlapping` pero el `raise ValidationError` está dentro de un string sin ejecutar | La validación de solapamiento de imputaciones nunca se aplica, pero sí su coste de cómputo | Confirmar si es intencional (ver sección 5) y, si no, sacar el `raise` del string |
| Medio | Múltiples ficheros (`leulit_actividad_base.py`, `leulit_actividad_base_dia.py`, `leulit_actividad_16bravo_dia*.py`) | SQL crudo con `.format()`/f-string en vez de parámetros | Hoy los valores son fechas/IDs internos (riesgo bajo), pero `data_calculation(fecha_inicio, fecha_fin)` es invocable por RPC | Migrar a `cr.execute(sql, params)` |
| Medio | Todo el addon | `threading.Thread(target=...)` sin `try/except` alrededor del cuerpo | Cualquier excepción en el hilo se pierde silenciosamente | Envolver el cuerpo del hilo en `try/except/log` |
| Medio | Todo el addon (decenas de ocurrencias) | `_logger.error()` usado para trazas de depuración normales | Uso normal del módulo | Bajar a `_logger.debug()`/`_logger.info()` |
| Medio | `models/actividad_aerea.py`, `models/actividad_aerea_planificada.py` | Múltiples `env.cr.commit()` intercalados dentro de la cadena de handlers | Si un handler posterior de la cadena falla, los anteriores ya han hecho commit | Mover los `commit()` fuera de la cadena, a un único punto tras completarla con éxito |
| Medio | `models/leulit_actividad_aerea.py` (`_time_flight_range1/2/3`), `leulit_actividad_16bravo_dia.py`, `leulit_actividad_16bravo_dia_planificada.py` | Computed fields `store=False` que lanzan una query (a veces SQL cruda) por registro y por columna | Tree view con N filas × 3 columnas de rango temporal → hasta 3N queries | Convertir a `store=True` con `@api.depends` o precalcular en batch |
| Medio | `models/leulit_time_worked.py:20-137` | 12 métodos compute independientes (`_get_horas_enero`…`_get_horas_diciembre`), cada uno relanzando sus propias búsquedas vía `get_horas_mensual` | Renderizar una fila de esta vista dispara hasta 12× las búsquedas necesarias | Un único compute que calcule los 12 meses de una vez |
| Medio | `models/leulit_actividad_16bravo.py:76-81` | `vuelo.updDataActividad()` — `leulit.vuelo` no define ese método (sólo `leulit.parte_escuela.updDataActividad(self, item)`, firma distinta) | Invocar `procesarVuelos`/`upd_datos_scheduled_action` (hoy sin invocador vivo detectado) | Corregir a `vuelo.updDataActividadAerea()` (el método real definido en `leulit_vuelo.py`) o al que corresponda |
| Medio | `views/*.xml` + `menu.xml` | 5 `ir.actions.act_window` (`leulit_20201211_1314_action`, `leulit_202012170843_action`, `leulit_20201130_1806_action`, `leulit_202012141016_action`, `leulit_20201128_1140_action`) sin ningún `menuitem` en el módulo | — | Confirmar si es intencional (ver sección 5) |
| Medio | `models/leulit_actividad_16bravo_dia.py:43-57` | `detalle_av()` sin `ensure_one()`; usa la última iteración de `for item in self` fuera del bucle | Botón "Detalle" pulsado sobre selección múltiple (si la UI lo permitiera) | `self.ensure_one()` al inicio |
| Medio | `views/leulit_actividad_16bravo_dia.xml`, `views/leulit_actividad_base.xml`, etc. | Botones "Detalle" ligados a métodos `detalle()`/`detalle_28d()`/`detalle_12m()`/`detalle_3m()`/`detalle_diasmes()` que sólo hacen `return True` | Usuario pulsa "Detalle" y no ocurre nada visible, sin error | Implementar la acción real o quitar el botón |
| Bajo | `models/leulit_time_worked.py:9`, `models/leulit_limit_working_time.py:9` | `import odoo.netsvc as netsvc` sin usar (existe en Odoo 17 pero es vestigial) | — | Eliminar el import |
| Bajo | `models/leulit_parte_escuela.py:3-4` | `from optparse import check_builtin` / `from tabnanny import check`, no usados, ajenos al dominio | — | Eliminar |
| Bajo | `models/account_analytic_line.py:276-279` y `:289-292` | Campo `leulit_partner_id` declarado dos veces idéntico | — | Eliminar la duplicidad |
| Bajo | Varios ficheros | Bloques grandes de código comentado (`leulit_vuelo.py:286-433`, `leulit_actividad_16bravo_dia.py`, `leulit_actividad_base_year.py`, vistas de búsqueda comentadas con `uid_ok`) | — | Limpiar o documentar por qué se conserva |
| Bajo | `models/leulit_actividad_base.py` (`updateWithVueloData`, `updateWithEscuelaData`, `getId`, `calc_coe_mayoracion`, `calc_delta_pre`, `calc_delta_pos`) | Implementación completa alternativa a la cadena de responsabilidad, sin invocadores externos (confirmado por grep) | — | Eliminar si de verdad está reemplazada por `actividad_laboral.py`/`actividad_aerea.py`, o documentar por qué se conserva |

## 3. Hallazgos críticos/altos — detalle

### C1. Vista SQL de `leulit.actividad_base_rutas` se crea con el nombre equivocado

`models/leulit_actividad_base_rutas.py:22-38`:

```python
def init(self):
    tools.drop_view_if_exists(self._cr, 'leulit_actividad_base_rutas')
    self._cr.execute(""" CREATE OR REPLACE VIEW leulit_leulit_actividad_base_rutas AS 
        ( ... )
    """)
```

`_name = "leulit.actividad_base_rutas"` implica que Odoo espera una tabla/vista llamada
`leulit_actividad_base_rutas`. El método `init()` **borra** esa vista (si existía de una
instalación anterior) y **crea otra con un nombre distinto** (`leulit_leulit_actividad_base_rutas`,
doble prefijo — probablemente copiado del nombre de la clase Python, que tiene el mismo typo:
`class leulit_leulit_actividad_base_rutas(models.Model)`). Tras cualquier `-u leulit_actividad`,
el modelo se queda sin tabla subyacente con el nombre correcto.

Esto además rompe la consulta SQL cruda en `models/leulit_actividad_base_dia.py:184-191`
(`_tiempo_facturable`), que referencia directamente `leulit_actividad_base_rutas` para fechas
anteriores al 31-12-2020 — lanzará `psycopg2.errors.UndefinedTable`.

**Fix propuesto:**

```python
def init(self):
    tools.drop_view_if_exists(self._cr, 'leulit_actividad_base_rutas')
    self._cr.execute(""" CREATE OR REPLACE VIEW leulit_actividad_base_rutas AS 
        ( ... )
    """)
```

Y de paso renombrar la clase Python (`leulit_leulit_actividad_base_rutas` → algo como
`LeulitActividadBaseRutas`) para que el typo no se vuelva a copiar.

### C2. `api.Environment.manage()` no existe en Odoo 17

Confirmado contra el código fuente de `odoo/api.py` en la rama `17.0` de GitHub: la clase
`Environment` no tiene ningún método `manage`. Este patrón (heredado de Odoo ≤9) aparece en:

- `models/leulit_actividad_16bravo.py:87-92` (`run_upd_datos_scheduled_action`)
- `models/leulit_calendar_event.py:52-66` (`run_upd_datos_actividad`)
- `models/leulit_actividad_base.py:401-471` (`do_data_calculation`)
- `models/leulit_parte_escuela.py:32-39` (`run_upd_datos_actividad`)
- `models/leulit_parte_escuela.py:216-238` (`run_recalcular_tiempos_imputados`)

```python
with api.Environment.manage():
    new_cr = self.pool.cursor()
    self = self.with_env(self.env(cr=new_cr))
    ...
```

`with api.Environment.manage():` lanza `AttributeError` en cuanto se ejecuta esa línea. Como todo
esto corre dentro de un `threading.Thread` lanzado y olvidado (`.start()` sin `join()`), el método
que lo invoca (p. ej. `run_recalcular_tiempos_imputados`) devuelve `{}`/`None` con éxito aparente,
y el error sólo queda en stderr del proceso — nadie se entera de que el recálculo no se hizo.

Hoy **no hay ningún botón, cron ni caller de otro módulo** que invoque estos 5 métodos (confirmado
por grep en todo el repo), así que es código muerto — pero por su nombre y por los valores de fecha
hardcodeados (`'2025-01-01'`, `'2026-01-01'`) todo apunta a que son herramientas de recálculo
manual pensadas para lanzarse a mano vía `odoo shell`, que es justo el flujo de trabajo que ya usa
este equipo para backfills (ver `README.md`/CLAUDE.md). Si alguien las invoca así, fallan.

**Fix propuesto** — reemplazar por el patrón ya correcto y usado en el mismo addon
(`models/leulit_vuelo.py:32-39`, `models/account_analytic_line.py:227-254`):

```python
db_registry = registry(self.env.cr.dbname)
with db_registry.cursor() as new_cr:
    env = api.Environment(new_cr, self.env.uid, self.env.context)
    ...
    new_cr.commit()
```

### C3. `intervals.add(...)` — las listas no tienen `.add()`

`models/actividad_laboral.py:50-68` (`SolapamientoHandler.handle`):

```python
intervals = []
for item in abds:
    intervals.add([item.inicio,item.fin])
intervals.append([request.iniciocalc, request.fin])
```

`intervals` es una `list`; `.add()` es de `set`. En cuanto `abds` (actividades del mismo
partner/fecha con otro `idmodelo`/`modelo`) tenga al menos un elemento, `AttributeError:
'list' object has no attribute 'add'`. `SolapamientoHandler` forma parte de la cadena
`initChainActividadLaboral` (`models/leulit_vuelo.py:78-84`), invocada desde
`leulit_parte_escuela.py:146` (hoy inalcanzable por el bug C4, ver debajo) y previsiblemente desde
`leulit_operaciones`/`leulit_vuelo` fuera de este addon — señalado pero no verificado por estar
fuera de alcance.

**Fix propuesto:**

```python
intervals.append([item.inicio, item.fin])
```

### C4. `leulit.parte_escuela` llama a métodos que sólo existen en otros modelos

`models/leulit_parte_escuela.py:143-175` (`updDataActividad`):

```python
def updDataActividad(self, item):
    handlerAL = item.initChainActividadLaboral()   # NO existe en leulit.parte_escuela
    ...
    handlerAA = item.initChainActividadAerea()      # NO existe en leulit.parte_escuela
```

`initChainActividadLaboral` sólo está definido en `models/leulit_vuelo.py:78-84` (clase
`ParteVuelo`, `_inherit = "leulit.vuelo"`). `initChainActividadAerea` está definido por separado en
`leulit_vuelo.py`, `leulit_calendar_event.py` y `account_analytic_line.py`, pero nunca en
`leulit_parte_escuela.py`. Al llamarlos sobre `item` (un recordset `leulit.parte_escuela`),
`AttributeError` garantizado.

Hoy `updDataActividad`/`updDataActividadFecha` (línea 179-184) sólo se invocan desde código
comentado dentro de `do_data_calculation` (`models/leulit_actividad_base.py:439-457`), así que es
otra ruta muerta — pero rota de raíz si se reactiva.

**Fix propuesto** — duplicar en `leulit_parte_escuela.py` la construcción de cadena que ya existe
en `leulit_vuelo.py`, adaptada a los campos de `leulit.parte_escuela` (el fichero ya importa
`actividad_laboral`/`actividad_aerea` en las líneas 12-13, así que las clases de los handlers están
disponibles):

```python
@api.model
def initChainActividadLaboral(self):
    chain1 = actividad_laboral.LaboralPreVueloHandler()
    chain2 = actividad_laboral.SolapamientoHandler()
    chain3 = actividad_laboral.ActividadBaseHandler()
    chain4 = actividad_laboral.ActividadBaseDiaHandler()
    chain1.set_next(chain2).set_next(chain3).set_next(chain4)
    return chain1

@api.model
def initChainActividadAerea(self):
    ...  # igual que leulit_vuelo.py:87-101
```

### C5. `unlink()` de `account.analytic.line` sólo borra el primer registro

`models/account_analytic_line.py:33-48`:

```python
def unlink(self):
    fecha = False
    for item in self:
        if item.guardia:
            ...
        if fecha:
            self.upd_datos_actividad(...)
            self.env['leulit.vuelo'].upd_datos_actividad(...)
        return super(AccountAnalyticLine, item).unlink()   # <-- return dentro del for
```

El `return` está dentro del bucle `for item in self:`. Al seleccionar varias líneas de imputación
en una vista lista y pulsar "Eliminar", Odoo llama a `unlink()` una vez con `self` = todas las
líneas seleccionadas; con este código sólo se borra la **primera**, el bucle termina con el
`return` de esa primera iteración, y las demás quedan sin eliminar — sin ningún error, el usuario
ve la operación como exitosa.

**Fix propuesto:**

```python
def unlink(self):
    for item in self:
        fecha = False
        if item.guardia:
            partner = self.env['res.partner'].search([('user_ids', '=', item.employee_id.user_id.id)])
            line = self.env['leulit.item_actividad_aerea'].search([
                ('partner', '=', partner.id), ('modelo', '=', 'account.analytic.line'), ('idmodelo', '=', item.id)
            ])
            fecha = line.fecha
            line.unlink()
            lines = self.env['leulit.item_actividad_aerea'].search([('partner', '=', partner.id), ('fecha', '=', fecha)])
            if not lines:
                self.env['leulit.actividad_aerea'].search([('fecha', '=', fecha), ('partner', '=', partner.id)]).unlink()
        if fecha:
            item.upd_datos_actividad(fecha_origen=fecha.strftime("%Y-%m-%d"), fecha_fin='2050-01-01', id_line=item.id)
            self.env['leulit.vuelo'].upd_datos_actividad(fecha_origen=fecha.strftime("%Y-%m-%d"), fecha_fin='2050-01-01')
    return super(AccountAnalyticLine, self).unlink()
```

### C6. `write()` de `account.analytic.line` sin `ensure_one()`

`models/account_analytic_line.py:51-55`:

```python
def write(self, values):
    res = super(AccountAnalyticLine, self).write(values)
    if self.guardia:
        self.updDataActividadAerea()
    return res
```

`self.guardia` accede a un campo por punto sobre un recordset que puede tener más de un registro
(cualquier `write()` masivo desde una vista lista). Odoo lanza `ValueError: Expected singleton`
y toda la escritura falla — incluida la parte ya delegada a `super().write()` en memoria, aunque el
error se produce después, con lo que la petición completa del usuario aborta.

**Fix propuesto:**

```python
def write(self, values):
    res = super(AccountAnalyticLine, self).write(values)
    for record in self:
        if record.guardia:
            record.updDataActividadAerea()
    return res
```

### C7. Zona horaria invertida en `leulit_calendar_event.getDateTimeUTC`

`models/leulit_calendar_event.py:82-90`:

```python
def getDateTimeUTC(self):
    try:
        madrid_tz = pytz.timezone("Etc/GMT+2")
        mtz = madrid_tz.localize(datetime(self.start.year, self.start.month, self.start.day, self.start.hour, self.start.minute))
        dt_utc = mtz.astimezone(pytz.timezone('UTC'))
        return dt_utc.replace(tzinfo=None)
```

Los nombres `Etc/GMT+N` de la base de datos de zonas horarias (tz database) tienen el signo
**invertido** por convención POSIX: `Etc/GMT+2` es UTC-2 (dos horas al oeste de UTC), no UTC+2. Es
un gotcha conocido de `pytz`/tz database, no una interpretación libre. Además es una zona fija sin
horario de verano, mientras que Madrid alterna entre UTC+1 (CET) y UTC+2 (CEST). El resultado son
desplazamientos de 3-4 horas respecto al valor correcto, todo el año.

Esta función alimenta `updDataPlanActividadAerea()` (línea 92-124), que calcula la actividad aérea
**planificada** (usada para los semáforos de horas de vuelo a 28 días/12 meses/3 meses y control de
descansos). En el mismo addon existe la implementación correcta, con la misma intención, dos veces:
`models/leulit_parte_escuela.py:81-93` y `models/account_analytic_line.py:75-87`, ambas usando
`pytz.timezone("Europe/Madrid")`.

**Fix propuesto:**

```python
madrid_tz = pytz.timezone("Europe/Madrid")
```

## 4. Plan de acción priorizado

1. **[Crítico]** `models/leulit_actividad_base_rutas.py` — corregir el nombre de la vista SQL en
   `init()` y añadir `ir.model.access` en `security.xml`.
2. **[Crítico]** `models/actividad_laboral.py:58` — `intervals.add(` → `intervals.append(`.
3. **[Crítico]** `models/account_analytic_line.py` — sacar el `return` de `unlink()` fuera del
   bucle (C5) y añadir `ensure_one`/iteración en `write()` (C6).
4. **[Crítico]** `models/leulit_calendar_event.py:84` — cambiar `"Etc/GMT+2"` por
   `"Europe/Madrid"`.
5. **[Crítico/Alto]** Sustituir el patrón `api.Environment.manage()` / `self.pool.cursor()` por
   `registry(dbname).cursor()` en los 5 puntos listados (C2) — aunque hoy son rutas muertas,
   corregirlas antes de que alguien las reactive o las llame a mano.
6. **[Crítico/Alto]** `models/leulit_parte_escuela.py` — implementar
   `initChainActividadLaboral`/`initChainActividadAerea` en el propio modelo (C4), o decidir si
   `updDataActividad`/`updDataActividadFecha` deben eliminarse por no usarse.
7. **[Alto]** `models/leulit_actividad_aerea.py:143-154` — corregir `_search_user_from_partner`
   para que use `operator`/`value` reales.
8. **[Alto]** `models/leulit_actividad_base_dia.py` — decidir si el bloque `updateData`/`getId`/
   `readActividades`/`calcTiempo` (con el global de módulo roto y el `item16B` indefinido) se
   elimina (recomendado, está duplicado por la cadena de `actividad_laboral.py`) o se reescribe.
9. **[Alto]** `models/leulit_actividad_base_dia.py:175-212` — añadir `@api.depends` a
   `_tiempo_facturable`.
10. **[Alto]** `models/leulit_vuelo.py:142-171` y `leulit_parte_escuela.py:48-78` — no hacer
    `self.env.cr.rollback()` completo dentro de `create_account_line`; usar un savepoint o cursor
    aislado, y loguear siempre la excepción real.
11. **[Medio]** Sacar los `env.cr.commit()` intermedios de las cadenas de `actividad_aerea.py` /
    `actividad_aerea_planificada.py` a un único commit al final de la cadena.
12. **[Medio]** Revisar y decidir sobre `_check_overlap_task` (¿reactivar la validación o eliminar
    el cómputo muerto?) — ver sección 5.
13. **[Medio]** Convertir a parametrizadas las SQL crudas con `.format()` en
    `leulit_actividad_base.py`, `leulit_actividad_base_dia.py`, `leulit_actividad_16bravo_dia*.py`.
14. **[Medio]** `models/leulit_time_worked.py` — unificar los 12 computes mensuales en uno solo.
15. **[Medio]** Revisar los 5 `ir.actions.act_window` sin menú (sección 5) y limpiar o enlazar.
16. **[Bajo]** Limpieza: imports muertos (`odoo.netsvc`, `optparse.check_builtin`,
    `tabnanny.check`), campo `leulit_partner_id` duplicado, bloques de código comentado grandes,
    y decidir sobre `models/leulit_actividad_base.py`'s `updateWithVueloData`/`updateWithEscuelaData`
    (sin invocadores).

## 5. Dudas / no verificable sin entorno

- **`_check_overlap_task` (`models/account_analytic_line.py:189-218`)**: el `raise
  ValidationError(...)` está dentro de un docstring, deshabilitado. ¿Fue intencional (se decidió no
  bloquear el solapamiento de imputaciones) o es un `TODO` a medio comentar que se quedó así?
  Necesito confirmación antes de tocarlo — si la regla de negocio real es "sí debe bloquear
  solapamientos", hay que sacar el `raise` del string; si no, se puede eliminar todo el bloque de
  cómputo (ahorra una búsqueda por cada guardado de línea de tiempo).

- **Acciones sin menú** (`leulit_20201211_1314_action`, `leulit_202012170843_action`,
  `leulit_20201130_1806_action`, `leulit_202012141016_action`, `leulit_20201128_1140_action`): no
  encuentro ningún `menuitem` en este módulo que las use. Puede ser deliberado (accesos técnicos,
  usados sólo desde debug/desarrollador, o enlazados desde otro módulo fuera de mi alcance que no
  he revisado) o vistas huérfanas de una reestructuración de menú. Pido confirmación antes de
  proponer eliminarlas.

- **`api.Environment.manage()` (5 puntos, hallazgo C2)**: confirmado por lectura del código fuente
  de Odoo 17 en GitHub que el método no existe — no he podido ejecutar el módulo para confirmar el
  traceback exacto en tiempo real. Recomiendo que la próxima vez que alguien ejecute
  `recalcular_tiempos_imputados` (o cualquiera de los otros 4) desde `odoo shell` en el entorno de
  pruebas, lo confirme y pegue el traceback aquí.

- **Alcance del `ir.rule`/`ir.model.access` sobre `leulit.RBase`**: todas las reglas de
  `security.xml` de este addon conceden CRUD completo (`read`/`create`/`write`/`unlink`) a
  `leulit.RBase`, que según `CLAUDE.md` prácticamente cualquier empleado tiene en su cadena de
  `implied_ids`. Esto incluye modelos que son en la práctica un registro de cumplimiento normativo
  de horas de vuelo (`leulit.actividad_aerea`, `leulit.item_actividad_aerea`,
  `leulit.actividad_16bravo*`). Es coherente con el patrón ya documentado en `CLAUDE.md` para este
  proyecto (rol base amplio + regla `RBase` con bypass explícito para roles privilegiados cuando
  hace falta restringir), así que no lo trato como hallazgo nuevo de seguridad, pero lo señalo por
  si se quiere revisar si `unlink` sobre estos modelos debería estar más restringido de cara a
  trazabilidad ante una inspección (EASA/Part-ORO). Es una decisión de negocio, no la tomo por mi
  cuenta.

- **Dependencias fuera de alcance**: `models/leulit_vuelo.py:181,198,226` llama a
  `self.getDateTimeUTC(fecha, hora, tz)` con 3 argumentos (incluyendo timezone del lugar de
  despegue). Ese método de 3 argumentos no está definido en ningún fichero de este addon — debe
  venir de `leulit_operaciones` (donde vive la definición base de `leulit.vuelo`). No lo he
  revisado por estar fuera del alcance pedido; lo señalo por si se quiere auditar también, ya que
  sería la tercera implementación de "hora local a UTC" del sistema.
