# Parte piloto privado — diseño

**Fecha:** 2026-09-01
**Estado:** aprobado en diseño, pendiente de plan de implementación
**Módulo nuevo:** `leulit_parte_privado`

## 1. Objetivo

Hay pilotos privados que no entran sus partes de vuelo en el ERP. Usuarios
autorizados transcribirán el PTV en papel mediante un formulario simplificado
("Parte piloto privado" en el menú Vuelos). Al pulsar **Finalizar**, el parte
recorre el ciclo completo (crear → firmar prevuelo → firmar cierre) y todos los
documentos (POV, PTV, F27 si aplica) se generan y firman **como si los hubiera
hecho el usuario del piloto** (`with_user`), quedando el vuelo en `cerrado`.

## 2. Invariante duro (innegociable)

**No se modifica absolutamente nada del workflow/procedimiento actual de
creación de vuelos.** Una regresión en el parte normal paraliza la operación
diaria de la compañía. Todo lo nuevo es un **workflow paralelo** que:

- reutiliza lo existente **llamándolo o importándolo, nunca editándolo**;
- vive en un módulo nuevo desinstalable;
- añade como máximo: campos nuevos vía `_inherit` (aditivo), un grupo nuevo en
  `leulit/groups.xml` (convención del repo, `<record>` añadido, solo-XML) y un
  menú nuevo.

Ficheros que quedan **intactos**: `vuelo_chain_postvuelo.py`,
`vuelo_chain_cerrado.py`, `leulit_esignature/vuelo.py`,
`leulit_esignature/SignatureDoc.py`, `leulit_operaciones/models/leulit_vuelo.py`
(salvo `_inherit` desde el módulo nuevo), vistas y menús actuales.

## 3. Decisiones cerradas (con el usuario, 2026-09-01)

- **Flujo de un solo paso**: Finalizar → cerrado con las dos firmas. Si algo
  falla, rollback total (una sola transacción), no queda nada a medias.
- **`tipo_actividad = 'NCO'` fijo.** Consecuencias verificadas en código:
  - pax permitidos (`vuelo_chain_postvuelo.py:73-75`);
  - `numpae` > 0 lo rechaza el handler (`:76-78`) → el form no lo muestra, se fija a 0 (decisión 2026-09-02, revisada tras la primera prueba).
- **Presupuesto se selecciona cada vez** en el form (depende del piloto).
  Domain estándar: `flag_flight_part=True`, `state='sale'`, `task_done=False`.
- **Meteo NO exigible** en este flujo. La cadena original la exige a todos
  (`vuelo_chain_postvuelo.py:225`); la exención vive SOLO en el handler nuevo
  del flujo paralelo. No se rellena meteo (campo vacío).
- **Performance NO necesaria** en este flujo (misma técnica: el handler nuevo
  no la comprueba).
- **W&B NO necesario** en este flujo. El PTV generado saldrá sin Masa/C.G.
  (el original en papel los lleva manuscritos).
- **PerfilesFormación omitido de momento** en la cadena paralela (decisión
  usuario 2026-09-01: "puedes omitirlos de momento"). Reactivable añadiendo el
  handler importado a la composición — un import y un eslabón.
- **Piloto privado = boolean nuevo `privado`** en `leulit.piloto`, marcado por
  responsables de operaciones en la ficha. Selector del wizard:
  `[('privado','=',True)]`.
- **Documentación**: el módulo lleva su `README.md` dentro de la carpeta.

## 4. Arquitectura

### 4.1 Estructura del módulo

```
addons/leulit_parte_privado/
  __manifest__.py            depends: leulit, leulit_operaciones, leulit_esignature
  README.md                  documentación funcional + técnica del módulo
  models/
    leulit_piloto.py         _inherit: privado = fields.Boolean("Piloto privado")
    leulit_vuelo.py          _inherit: privado_introducido_por = fields.Many2one('res.users')
  wizard/
    parte_privado_wizard.py  TransientModel leulit.parte.privado.wizard + finalizar()
    parte_privado_wizard_view.xml
  chains/
    vuelo_chain_privado.py   composición de cadenas A y B + DatosGeneralesPrivadoHandler
  views/
    leulit_piloto_view.xml   xpath aditivo: check "Piloto privado" junto a Freelance
  security/
    ir.model.access.csv      ACL del wizard para el grupo nuevo
  menu.xml                   "Parte piloto privado" bajo Vuelos, grupo nuevo
```

Único cambio fuera del módulo: `addons/leulit/groups.xml` recibe el grupo
`ROperaciones_parte_privado` (record añadido; actualización solo-XML de
`leulit`).

### 4.2 Datos y acceso

- Grupo `ROperaciones_parte_privado` en `leulit/groups.xml`, asignable a los
  usuarios autorizados. Sin `implied_ids` hacia roles de operaciones: quien lo
  tenga ve el menú nuevo y nada más de lo que ya no viera.
- Menú `Parte piloto privado` con
  `parent="leulit_operaciones.leulit_20201023_1053_menuitem"` (menú Vuelos),
  `groups` = grupo nuevo. Abre el wizard.
- ACL: CRUD del wizard para el grupo nuevo. `leulit.vuelo` ya tiene CRUD para
  `RBase` (`leulit_operaciones/security.xml`), no hace falta tocar nada.

### 4.3 Campos del wizard (mapeo PTV papel → modelo)

Inputs del usuario:

- `fechavuelo` (date, default hoy)
- `helicoptero_id` (m2o)
- `piloto_id` (m2o `leulit.piloto`, domain `privado=True`)
- `presupuesto_vuelo` (m2o `sale.order`, domain estándar flag_flight_part)
- `vuelo_tipo_id` (m2o `leulit.vuelostipo` → al crear genera la
  `vuelo_tipo_line`; cubre el check "No hay comentario logbook")
- `numpax` (int, default 1)
- `lugarsalida`, `lugarllegada` (m2o helipuerto)
- `horasalida` (float hora local) y `tiemposervicio`; `horallegada` = salida + servicio y `airtime` = servicio − 6 min se calculan en el form, solo lectura (decisión 2026-09-02).
- combustible (decisión 2026-09-02, sin campos en el form): `oilqty` = 0 fijo;
  `fuelqty` = 0 salvo que el remanente no cubra `combustibleminimo`, entonces
  se reposta lo justo (+1 l.); `fuelllegada` estimado con `_calc_fuelllegada`.
- `tacomllegada` (no-EC120B) **o** `ngvuelo` + `nfvuelo` (EC120B; constraint
  existente: > 0 y ≤ 4) — visibilidad condicionada al modelo del helicóptero
- constraints existentes que siguen aplicando: airtime múltiplo de 6 min, ≤ tiemposervicio, ≤ 3 h
- `comentarios` (O.V., texto libre, opcional)
- `declaracion` (boolean único: "Inspección prevuelo, briefing, NOTAM y
  debriefing realizados" → marca `checklist_realizado`, `briefing_realizado`,
  `notam_revisado`, `checklist_postvuelo_realizado`)

Sin meteo, sin W&B, sin performance, sin `ruta_id`, sin alternativos, sin
alumno/verificado/operador/supervisor.

### 4.4 Defaults y derivados al crear el vuelo

Constantes: `tipo_actividad='NCO'`, `numtripulacion=1`,
`asiento_pic='pic_right'`, `reservasfuel='30'`, `rodaje='0'`,
`contingencia='0'`, `distancia_alternativo=0`, `uso_gancho=0`, `landings=1`,
`nightlandings=0`, `arlanding=0`, `sling_cycle=0`, `ifr=False`, `nv=False`,
`balsa/flotadores/chalecos=False` (sin ruta no aplica el check water_zone).

Derivados ejecutando server-side la lógica existente (onchange
`helicoptero_id` + motor `calculosFuel`, llamados, no copiados):

- del helicóptero: emptyweight/moments/arms/pesomax, `velocidadprevista`,
  `consumomedio_vuelo`;
- del último vuelo cerrado de la máquina: `editfuelrem` → `fuelsalida`
  (= editfuelrem + fuelqty), `tacomsalida`, `combustibleextra`;
- del motor de fuel: `tiempoprevisto` (= horallegada − horasalida; la cadena
  exige ≤ 3 h), `distanciatotalprevista` (tiempo × velocidad; exige ≠ 0),
  `horallegadaprevista`, `combustibleminimo`, `combustiblelanding`,
  `combustibletrayecto` y conversiones kg/gal.

### 4.5 Secuencia de `finalizar()`

1. **Resolver usuario del piloto**: `piloto_id.partner_id.user_ids` activo.
   Sin usuario activo → `UserError` claro ("El piloto X no tiene usuario
   activo en el ERP; no se puede firmar en su nombre").
2. **Crear** `leulit.vuelo` `with_user(usuario_piloto)` con inputs + defaults +
   derivados (§4.4). `create_uid` y chatter quedan a nombre del piloto.
3. **Cadena paralela A** (prevuelo → postvuelo), compuesta en
   `chains/vuelo_chain_privado.py` con las clases **importadas** de
   `vuelo_chain_postvuelo.py`:
   - ComprobacionTripulacionEnVuelosPostvuelo, ComprobacionChecks,
     ComprobacionTripulantesTipoActividad, ComprobacionUsuarioPiloto,
     ComprobacionHelicoptero, ComprobacionOverlapPartesEscuelaVuelo,
     ComprobacionDatosCombustible — tal cual;
   - **`DatosGeneralesPrivadoHandler` (nuevo)**: mismos checks que el original
     (`vuelo_chain_postvuelo.py:209-247`) **menos** meteo (:225),
     `valid_*cg` (:235), performance (:237) y `pasajeros_wb` (:239). Mantiene:
     distancia ≠ 0, tripulación ≠ 0, tiempoprevisto ≤ 3 h, NOTAM, horasalida,
     tacomsalida (no-EC120B), oilqty ≥ 0, horas_remanente, water_zone (no
     aplica sin ruta), vuelo_tipo_line;
   - Omitidos: ComprobacionParteEscuela (no hay escuela en NCO privado),
     **ComprobacionPerfilesFormacion (de momento — ver §3)**.
4. **Firma 1** (`with_user(usuario_piloto)`): estado → `postvuelo` y
   generación/firma de POV + PTV vía la maquinaria existente de
   `leulit_esignature` (patrón `pruebas_checksignatureRef`: OTP real del
   piloto con `get_otp()`, `buildPdfSigned`), `control_firma='firmado'`.
   F27 automático si EC120B con `checklist_prevuelo_BFF` (usa `piloto.firma`;
   prerequisito de ficha).
5. **Cadena paralela B** (postvuelo → cerrado), handlers de
   `vuelo_chain_cerrado.py` importados **tal cual** — todos satisfacibles con
   los datos capturados: ComprobacionPresupuesto, ComprobacionChecks,
   ComprobacionUsuarioPiloto, ComprobacionDescanso, ComprobacionHelicoptero,
   ComprobacionDatosGenerales, ComprobacionDatosCombustible,
   UpdateProximoVuelo. Se omite `ComprobacionOverlapPartesEscuelaVuelo`: en
   este punto el vuelo ya está en `postvuelo` y la búsqueda del handler no
   excluye su propio id, así que se solaparía consigo mismo; además
   `initChainToCerrado` (flujo web) tampoco lo corre al cerrar, así que
   omitirlo mantiene la paridad. El solape ya lo comprobó la cadena A. Nota:
   nuestra composición conecta también los eslabones que el `initChainToCerrado`
   original dejó desconectados por el bug conocido (chain7 asignado dos veces)
   — sin tocar el original, que se queda con su bug.
6. **`verificar_actividad_aerea`** del partner del piloto (método existente,
   llamado igual que hace `firmar_doc_parte_vuelo` al cerrar).
7. **Firma 2** → estado `cerrado`, POV/PTV finales firmados.
8. **Trazabilidad**: `privado_introducido_por = env.user` (el usuario
   autorizado real) + nota en el chatter del vuelo: "Parte introducido por
   {usuario} mediante Parte piloto privado en nombre de {piloto}".
9. Todo dentro de una transacción del wizard. **Atención en el plan**: varios
   handlers hacen `request.env.cr.commit()` — la composición paralela debe
   ejecutarse con savepoint propio o validar ANTES de crear nada lo que sea
   validable, y documentar qué queda commiteado si falla un eslabón tardío.

### 4.6 Firma impersonada — los tres cerrojos

Los tres puntos relativos a uid se abren con `with_user(usuario_piloto)`:

1. `ComprobacionUsuarioPilotoHandler` compara con `request.uid`;
2. `uidCanSign` (SignatureDoc) exige usuario del piloto/supervisor;
3. la generación OTP usa `env.user`.

`firmado_por` en el signaturedoc queda como el partner del piloto. Precedente
en el propio código: `pruebas_checksignatureRef` y los parámetros
`hack_firmado_por`/`hack_estado` de buildPOVPdf/buildPTVPdf/buildF27Pdf.

**Nota de compliance** (decisión del operador, registrada): la spec
2026-08-18 mantenía el gesto deliberado de teclear el OTP como parte del
procedimiento de firma; este flujo lo automatiza para pilotos privados. El
contrapeso es la trazabilidad del §4.5.8 (campo + chatter): quién introdujo
qué queda siempre reconstruible.

## 5. Prerequisitos de datos (bloquean si faltan)

Por piloto privado: `res.users` activo enlazado (partner → user), check
`privado` marcado, firma escaneada en ficha (`piloto.firma`, solo si volará
EC120B por el F27). Por helicóptero: operativo (no taller, sin anomalías sin
firmar), `consumomedio` y `velocidad` en ficha, horas de potencial
remanentes. Presupuesto NCO en estado `sale` con `flag_flight_part`.
Descansos del piloto que cuadren (cadena B los valida con datos reales).

## 6. Verificación

Tests `TransactionCase` en `leulit_parte_privado/tests/`:

- ciclo feliz: wizard → finalizar → vuelo `cerrado`, `control_firma='firmado'`,
  POV+PTV existentes con `firmado_por` = partner del piloto,
  `privado_introducido_por` = usuario autorizado, nota en chatter;
- negativos: usuario sin grupo (sin acceso a menú/wizard), piloto sin usuario
  activo, piloto no marcado `privado` (fuera del domain), NG > 4 (constraint),
  airtime no múltiplo de 6 min, sin presupuesto, tacomllegada ≤ tacomsalida;
- invariante: los ficheros de cadenas/esignature originales no cambian
  (garantizado por construcción: el módulo no los toca).

Sin Odoo local: comandos para el entorno de pruebas del usuario:

```bash
docker exec -ti helipistas_odoo_17 odoo -i leulit_parte_privado -d productiu --stop-after-init
./upd_module.sh leulit dev        # grupo nuevo en groups.xml (solo XML)
docker exec -ti helipistas_odoo_17 odoo -u leulit_parte_privado -d productiu --test-enable --test-tags=/leulit_parte_privado --stop-after-init
```

## 7. Fuera de alcance

- Modificar cualquier pieza del flujo actual de vuelos (invariante §2).
- Meteo, W&B, performance y perfiles de formación en el flujo privado.
- App móvil (la spec 2026-08-18 es otra iniciativa).
- Facturación/gestión de los presupuestos NCO (se seleccionan, no se crean).
