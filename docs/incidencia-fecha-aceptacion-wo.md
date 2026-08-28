# Posible pérdida de la fecha de aceptación en órdenes de trabajo

**Fecha del análisis:** 21 de agosto de 2026
**Modelo afectado:** `maintenance.request` (Órdenes de trabajo / Peticiones de mantenimiento)
**Módulo:** `leulit_taller`

---

## 1. Resumen en una frase

Cuando una orden de trabajo se cierra pulsando directamente sobre la etapa
final en la barra de estados, sin haber pasado antes por una etapa intermedia,
el sistema calcula la **fecha de aceptación** pero **no llega a guardarla**: la
orden queda cerrada con ese campo vacío, sin ningún error ni aviso en pantalla.

Falta confirmar con taller si eso es un problema real de negocio o si esas
órdenes efectivamente nunca se aceptaron.

---

## 2. Las etapas de una orden de trabajo

En producción hay cinco etapas configuradas. Cada una lleva internamente dos
marcas que el usuario no ve:

- **Nueva solicitud** — no aceptada, no cerrada
- **En proceso** — aceptada, no cerrada
- **CRS incompleto** — aceptada, no cerrada
- **Reparado** — aceptada **y** cerrada
- **Desechar** — aceptada **y** cerrada

El punto importante, y es la clave de todo el asunto: **"Reparado" y "Desechar"
están marcadas como aceptadas**. No existe ninguna etapa cerrada que no esté
aceptada.

De ahí se deduce que, por diseño, **toda orden de trabajo que llegue a
"Reparado" o "Desechar" debería tener fecha de aceptación**. Si aparece vacía,
o bien se perdió, o bien la etapa está mal configurada.

---

## 3. Qué hace el sistema al cambiar de etapa

La barra de estados de la orden de trabajo es **pulsable**: se puede saltar de
una etapa a otra haciendo clic directamente sobre ella, sin guardar entre medias.

Al cambiar de etapa, el sistema ejecuta automáticamente estas acciones si la
etapa nueva está marcada como aceptada:

1. Si la orden **no estaba aceptada antes** → escribe la fecha y hora actuales
   en **Fecha aceptación**.
2. Pone el helicóptero en estado **"En taller"**.
3. Copia el **horómetro** actual del helicóptero al campo Horómetro de la orden.

Nada de esto se guarda todavía: son cambios en pantalla, a la espera de que el
usuario pulse Guardar.

---

## 4. Dónde está el fallo

Los campos **Fecha aceptación** y **Horómetro** están configurados para
bloquearse (ponerse en gris, no editables) en cuanto la orden pasa a una etapa
cerrada. Es una decisión razonable: una orden cerrada no se toca.

El problema es cómo funciona Odoo 17 por debajo: **al guardar, el programa
descarta el contenido de todos los campos que en ese momento están bloqueados**.
No los envía al servidor. Es una norma general de la versión 17, no un error de
nuestro desarrollo.

Y aquí las dos cosas chocan:

- Al pulsar sobre **"Reparado"**, el sistema **calcula** la fecha de aceptación
  (porque la etapa está marcada como aceptada)...
- ...y **en ese mismísimo instante** los campos se bloquean (porque la etapa
  también está marcada como cerrada).
- Al guardar, el valor recién calculado se descarta.

El resultado: la orden se guarda cerrada, con la fecha de aceptación vacía. **En
pantalla el usuario llega a ver la fecha rellenada** antes de guardar, lo que
hace el fallo especialmente difícil de detectar.

### Cuándo NO ocurre

Si la orden pasa primero por **"En proceso"** o **"CRS incompleto"** (aceptadas
pero no cerradas), en ese momento los campos siguen desbloqueados y la fecha
**sí** se guarda correctamente. Al cerrarla después, la fecha ya está en la base
de datos y no se pierde.

**Por eso el fallo depende por completo del camino que siga cada persona**: quien
cierra las órdenes paso a paso no lo sufre; quien las cierra de un solo clic, sí.

---

## 5. Qué dicen los datos de producción

Consultado el 21 de agosto de 2026 sobre la base de datos real.

**Órdenes en etapa "Reparado" o "Desechar": 297 en total**

- Con fecha de aceptación: 163
- **Sin fecha de aceptación: 134**

Repartidas por año de creación, las que están sin fecha:

- 2023: 2
- 2024: 47
- 2025: 44
- 2026: 41

**Acotando a la era Odoo 17** (órdenes creadas desde el 6 de octubre de 2025,
cuando se puso en marcha el sistema actual — las anteriores vienen migradas de
la versión previa y no sirven para juzgar el comportamiento de hoy):

- Con fecha de aceptación: 49
- **Sin fecha de aceptación: 53**

Es decir, en torno a la mitad de las órdenes cerradas no tienen fecha de
aceptación, y la proporción se mantiene estable a lo largo del tiempo.

Ejemplos concretos, todos cerrados y sin fecha de aceptación, para que taller
pueda contrastarlos contra sus registros en papel:

- `OIK260713` — creada 24-jul-2026, cerrada 12-ago-2026
- `ILV260810` — creada 10-ago-2026, cerrada 12-ago-2026
- `KYM260702` — creada 02-jul-2026, cerrada 12-ago-2026
- `ILV260716` — creada 16-jul-2026, cerrada 11-ago-2026
- `MHF260724` — creada 24-jul-2026, cerrada 10-ago-2026

### Honestidad sobre lo que estos números demuestran y lo que no

El mecanismo del fallo está **verificado línea a línea en el código** — de eso no
hay duda. Lo que estas cifras **no** demuestran por sí solas es que las 134
órdenes se hayan quedado sin fecha por esta causa concreta:

- La proporción es parecida antes y después de octubre de 2025, es decir,
  también en la versión anterior del ERP. Eso puede significar que el mismo
  fallo ya existía antes, o que hay otra explicación distinta para las órdenes
  antiguas.
- Los registros anteriores a octubre de 2025 llegaron por migración de datos y
  pueden haber perdido el campo por el camino, sin relación con este fallo.

Lo que sí sostiene el análisis, con independencia de las cifras: **todas las
etapas cerradas están marcadas como aceptadas, luego ninguna orden cerrada
debería tener la fecha vacía**. Que la mitad la tenga vacía indica que algo la
está perdiendo.

---

## 6. Y el horómetro

El mismo mecanismo afecta al campo **Horómetro**, pero el efecto práctico es
distinto y bastante menor:

- El horómetro se rellena **al crear** la orden desde el asistente de creación,
  y ese valor se guarda correctamente porque lo pone el servidor, no la pantalla.
- Lo que se pierde es únicamente el **refresco** que el sistema intenta hacer al
  cambiar de etapa.
- Como el helicóptero no vuela mientras está en taller, ese refresco normalmente
  no cambiaría nada.

Por eso los datos de horómetro están completos aunque falten fechas de
aceptación: proceden de dos sitios distintos.

**Aun así hay una decisión de negocio que corresponde a taller**, y este
documento no la prejuzga:

> ¿Qué horómetro debe quedar registrado en una orden de trabajo: el de cuando el
> helicóptero **entró** en taller, o el de cuando se **cerró** la orden?

Hoy, de hecho, queda el de la entrada. El código parece pretender lo segundo,
pero no lo consigue. Antes de tocarlo hay que saber cuál de los dos es el
correcto, porque cambiarlo afectaría a todas las órdenes futuras y crearía una
inconsistencia con el histórico.

---

## 7. Lo que hay que validar con el responsable de taller

Estas son las preguntas que deciden si esto se arregla, cómo, y con qué prioridad:

1. **¿Cómo cerráis habitualmente una orden de trabajo?** ¿Pasando por "En
   proceso" y luego a "Reparado", o pulsando directamente sobre "Reparado" desde
   "Nueva solicitud"?

2. **¿Qué significa para vosotros la Fecha de aceptación?** ¿Es un dato de
   trazabilidad que debe existir siempre en una orden cerrada, o un campo
   informativo que a veces legítimamente no aplica?

3. **¿Os consta que a estas 134 órdenes les falte ese dato?** ¿Lo habíais
   detectado? ¿Lo suplís con otro registro (parte en papel, CRS, otra fecha del
   sistema)?

4. **¿Tiene consecuencias de cara a una auditoría Part-145** que una orden de
   trabajo cerrada no tenga fecha de aceptación?

5. **Horómetro: ¿el de entrada o el de cierre?** (pregunta del apartado 6)

6. Si el dato es obligatorio, **¿hay que recuperar el histórico?** Los 134
   registros no se pueden reconstruir de forma automática y fiable: habría que
   decidir si se dejan vacíos, si se rellenan a mano desde los partes de papel,
   o si se aproximan con la fecha de creación de la orden (con el riesgo de
   inventar un dato que no es).

---

## 8. Cómo reproducirlo en el entorno de pruebas

Para verlo en vivo antes de decidir nada. **Hacerlo en pruebas, nunca en
producción.**

1. Crear una orden de trabajo nueva. Queda en **"Nueva solicitud"**.
2. Guardarla.
3. Sin tocar nada más, **pulsar directamente sobre "Reparado"** en la barra de
   estados de arriba.
4. **Mirar la pantalla:** el campo Fecha aceptación aparece relleno con la fecha
   y hora de ahora mismo. Los campos están en gris.
5. Pulsar **Guardar**.
6. **Recargar la página** (F5).
7. Resultado esperado si el análisis es correcto: **el campo Fecha aceptación
   está vacío**.

Y el contraste, para confirmar que el camino largo sí funciona:

1. Otra orden nueva en **"Nueva solicitud"**.
2. Pulsar **"En proceso"** → la fecha se rellena y los campos siguen editables.
3. **Guardar**.
4. Ahora pulsar **"Reparado"** y guardar.
5. Recargar. Resultado esperado: **la fecha sigue ahí**.

---

## 9. Opciones de corrección

Ninguna se ha aplicado todavía. Están a la espera de la validación de taller.

**Opción A — Marcar los campos para que se guarden aunque estén bloqueados**

Añadir el atributo `force_save="1"` a los dos campos en la vista. Son dos
palabras en un fichero. Sigue viéndose todo en gris, pero el valor se guarda.

Es la solución que ya se ha aplicado esta misma semana a un fallo idéntico en
las anomalías, y el patrón ya se usa en una veintena de sitios del ERP.

Inconveniente: solo arregla el formulario web. Si algún día una app o una
integración crea órdenes de trabajo, no las cubre.

**Opción B — Sellar la fecha en el servidor**

Que sea el servidor quien ponga la fecha de aceptación al detectar el cambio a
una etapa aceptada, en lugar de la pantalla. Es más código, pero es inmune a
cómo se comporte el navegador, y es lo que ya se hace en ese mismo fichero con
la fecha de cierre (`close_date`).

Recomendable si la fecha de aceptación es un dato de trazabilidad obligatorio:
un dato que una auditoría puede pedir no debería depender de qué campos decide
enviar el navegador.

**Opción C — Las dos**

La corrección de pantalla para que el comportamiento sea correcto de inmediato,
y el sellado en servidor como red de seguridad.

**Opción D — No tocar nada**

Si taller confirma que las órdenes sin fecha de aceptación son correctas y que
el dato no aporta nada, la mejor solución es la contraria: quitar el campo de la
pantalla, para que nadie lo interprete como un hueco.

---

## Anexo técnico

Para quien vaya a implementar la corrección. El resto del documento no lo
necesita.

**La regla de Odoo 17.** El cliente web no envía al servidor el valor de un
campo que, en el momento de guardar, tenga activo el modificador `readonly` en
la vista, salvo que el `<field>` lleve `force_save="1"`. Si el campo es
`required`, el guardado revienta con una violación de `NOT NULL`; si no lo es,
el valor se pierde en silencio. Este es el segundo caso.

**Los cuatro elementos que se combinan:**

1. `addons/leulit_taller/views/maintenance_request.xml:25`
   ```xml
   <field name="stage_id" widget="statusbar" options="{'clickable': '1'}" invisible="((archive))" />
   ```
   La barra es pulsable: el modificador se reevalúa en el cliente sin recarga.

2. `addons/leulit_taller/models/maintenance_request.py:130-132`
   ```python
   accepted = fields.Boolean(related='stage_id.accepted')
   done     = fields.Boolean(related='stage_id.done')
   ```
   Ambos `related` sin `store=True`, y `done` está presente (invisible) en la
   vista, línea 59 → se recalcula dentro del propio onchange.

3. `addons/leulit_taller/models/maintenance_request.py:45-52`
   ```python
   @api.onchange('stage_id')
   def onchange_stage(self):
       if self.stage_id:
           if self.accepted:
               if not self._origin.accepted:
                   self.fecha_aceptacion = datetime.now()
               self.helicoptero.statemachine = "En taller"
               self.horometro = self.helicoptero.airtime
   ```

4. `addons/leulit_taller/views/maintenance_request.xml:61,66`
   ```xml
   <field name="fecha_aceptacion" widget="date" invisible="((not accepted))" readonly="((done))" />
   <field name="horometro" readonly="((done))" />
   ```
   Sin `force_save`.

**Secuencia:** clic en etapa 3 o 4 → `onchange_stage` entra en la rama
`self.accepted` y escribe los dos campos → `done` (related no almacenado) pasa a
`True` en el mismo onchange → los modificadores `readonly="((done))"` se
reevalúan a `True` → al guardar, el cliente excluye ambos campos del payload.

**Origen del horómetro que sí sobrevive:**
`addons/leulit_taller/models/leulit_wizard_create_maintenance_request.py:30`
lo fija en servidor al crear la orden.

**Etapas en producción** (`maintenance.stage`): id 1 *Nueva solicitud*
(accepted=False, done=False) · id 2 *En proceso* (True, False) · id 5 *CRS
incompleto* (True, False) · id 3 *Reparado* (True, **True**) · id 4 *Desechar*
(True, **True**).

**Caso hermano ya corregido.** El mismo mecanismo, con crash en lugar de pérdida
silenciosa por tratarse de un campo `required`, se corrigió el 21-ago-2026 en
`leulit.anomalia` (commit `c664b788`): `helicoptero_id` tenía
`readonly="estado in [...] or vuelo_id"` y el onchange de `vuelo_id` lo
rellenaba. La regla general quedó documentada en
`.github/copilot-instructions.md`, sección *"`readonly` en vistas: Odoo 17 NO
guarda el valor"*.
