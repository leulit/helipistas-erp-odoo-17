# Propuesta de roles y autorizaciones — ERP Odoo 17

Estado: **borrador para validación**. Pendiente de revisión por RCC antes de implementar.
Fecha: 2026-09-07. Origen: organigrama departamental de Helipistas + auditoría del ERP en producción.

Este documento **no** describe lo implementado. Describe lo que se propone implementar.

---

## 0. Diagnóstico del estado actual

Todos los números salen de producción y del repositorio, no de estimaciones.

### 0.1 Los grupos actuales no dan permisos: dan visibilidad

- **19 líneas** de `ir.model.access` propias en todo el repositorio.
- **9** reglas `ir.rule` propias.
- **299** apariciones de `groups="..."` en vistas y menús.

El permiso real de lectura/escritura lo conceden los grupos estándar de Odoo
(`base.group_user`, `stock.*`, `hr.*`, `mgmtsystem.*`, `project.*`). Los grupos
`leulit_*` casi solo esconden y muestran menús.

**Consecuencia:** el control de acceso actual no resiste el acceso por API ni la
importación/exportación de datos. Un usuario que no ve un menú sí puede leer el
modelo por JSON-RPC. Si Part-IS entra en juego, esto deja de ser deuda estética.
*A confirmar por RSI/RCC — no es una lectura reglamentaria de este documento.*

### 0.2 La jerarquía lineal modela un escalafón que no existe

Cadena actual en Operaciones:

```
piloto_externo -> alumno -> operador -> piloto -> responsable -> gestor
```

Sobre **135 usuarios internos activos**: *Piloto Externo* lo tienen **110**,
*Alumno (Operaciones)* **101**, *Alumno (Escuela)* **122**. El Responsable de
Operaciones es, formalmente, alumno y piloto externo. Un grupo que tiene el 90%
de la plantilla no informa de nada.

### 0.3 Nombres no discriminantes

Hay **8 grupos llamados "Base"** y **6 llamados "Responsable"**, cada uno en una
categoría distinta. Sin abrir el XML no se sabe qué protege ninguno.

### 0.4 Cuatro vocabularios de roles conviviendo

1. **Grupos legacy** (`RBase_*`, `ROperaciones_*`, `RTaller_*`…) — **vivos**, 49 grupos, 299 referencias en vistas.
2. **`addons/leulit/roles_2026.xml`** — 26 grupos de la matriz *"Roles ERP Ed1 06_2026.xlsx"*.
   Añadido el 2026-06-30, **comentado en el manifest el 2026-07-05** (`ffc923d9`). **Cero** ACL, `ir.rule` o menús lo referencian.
3. **`addons/leulit/utilitylib.py:28-36`** — `ROL_DIRECCION`, `ROL_SUPERADMIN`, `ROL_RESP_FORMACION`,
   `ROL_RESP_SMS`, `ROL_RESP_OPERACIONES`, `ROL_FINANCIERO`, `ROL_PILOTO_EXTERNO`, `ROL_COMERCIAL`,
   `ROL_RESP_COMERCIAL`. **Cero usos. Código muerto.**
4. **`PV_*`** en `addons/leulit_operaciones/models/leulit_vuelo.py:32-72` — `PV_PILOTO`, `PV_ALUMNO`,
   `PV_OPERADOR`, `PV_INSTRUCTOR`, `PV_VERIFICADO`. **Vivo y correcto**: calcula el rol de una persona
   *respecto a un vuelo concreto*. Es el patrón que este documento generaliza. Solo existe en vuelos.

No es que el esquema esté mal diseñado: hay cuatro intentos superpuestos y solo uno se terminó.

### 0.5 Censo de usuarios

De **135 usuarios internos activos** (`share = False`):

- **40** son personal (`RBase_employee`), que cuadra exacto con los 40 empleados con usuario.
- **83** son alumnos de escuela que **no** son personal.
- El resto (una docena) son pilotos externos, propietarios y trabajadores externos.

Hay **42 empleados activos** y **157 alumnos activos**, de los cuales **38 son empleados**:
la formación continua del personal ya está ocurriendo, y el ERP la modela metiendo a cada
empleado por la puerta de la escuela.

**Cuentas dormidas:** **25** usuarios llevan más de un año sin entrar; **44** más de seis meses.
Ninguno sin entrar jamás. Es un hallazgo de auditoría de accesos por sí solo, independiente
del rediseño de roles.

### 0.6 Multicompañía

Tres compañías: **Helipistas S.L. (1)**, **Icarus Manteniment S.L. (2)**, **Leulit S.L. (3)**.

- **129** usuarios tienen Helipistas por defecto, **6** Icarus, **0** Leulit.
- **21** usuarios pueden acceder a Icarus además de a Helipistas.
- **9** alcanzan Leulit.
- Nadie tiene Icarus o Leulit en solitario.

### 0.7 El expediente formativo cuelga del sitio equivocado

`leulit.perfil_formacion` tiene **867 perfiles** no plantilla en producción. Sus anclajes son
`piloto` (`leulit.piloto`) y `alumno` (`leulit.alumno`): **866 de 867** cuelgan de uno de los dos,
**ninguno de `hr.employee`**. No existe el concepto "expediente formativo de un empleado".

`leulit_escuela/models/leulit_alumno.py:493` (`alta_alumno`) al dar de alta a un alumno:

- crea **siempre** un `leulit.piloto`, sea mecánico, contable o comercial;
- busca 6 grupos **por su nombre en castellano** (`('name','=','Alumno')`, `('name','=','Base')`…);
- hardcodea `'company_id': 1`, ignorando Icarus;
- usa el número mágico `sel_groups_1_9_10: 10`.

Es el único punto del código que resuelve grupos por nombre. El resto usa `has_group()` con xmlid,
que sobrevive a un renombrado.

---

## 1. El modelo: tres ejes

El error del esquema actual es mezclar en una sola dimensión tres cosas distintas.

### Eje 1 — PUESTO

Lo que una persona **es** en el organigrama. Es lo único que se asigna a mano a un usuario.
No lleva permisos propios: los compone.

Un grupo por casilla del organigrama, aunque varios compartan capacidades idénticas. El valor
del eje es poder responder a un auditor *"¿qué puede hacer un SIC?"* señalando un grupo.

### Eje 2 — CAPACIDAD

Lo que una persona **puede hacer** en el ERP. Es donde viven los permisos, los `groups=` de
las vistas y las ACL. Los puestos las componen vía `implied_ids`.

### Eje 3 — SUJETO

De qué registros una persona **es protagonista**: su expediente, sus tareas, sus documentos,
sus partes, sus evaluaciones. **No es un grupo**: es dato + `ir.rule`.

Ya existe implementado en vuelos (`PV_*`). Este documento lo extiende al resto.

### Por qué tres y no dos

Un mecánico que hace un curso de Factores Humanos no es "alumno": es un mecánico **con un
expediente formativo**. El DR también hace cursos. Con dos ejes hay que inventarle un rol
"alumno" a todo el mundo — que es exactamente lo que pasa hoy, con 122 de 135 usuarios en
el grupo *Alumno*.

**"Alumno" desaparece como rol.** Tener expediente es un dato. Lo que separa a un alumno
externo de un empleado es no ocupar ninguna casilla del organigrama.

---

## 2. Catálogo del eje PUESTO

36 puestos, espejo del organigrama. Prefijo propuesto: `POS_`.
Categoría Odoo propuesta: **"Puesto (organigrama)"**.

### Dirección general y control de conformidad
- `POS_dr` — Director Responsable (Accountable Manager)
- `POS_rcc` — Responsable de Control de Conformidad
- `POS_rcc_adjunto` — Adjunto RCC
- `POS_auditor_interno` — Auditor Interno *(no existe hoy en el ERP)*
- `POS_rs` — Responsable de Seguridad Operacional
- `POS_rs_adjunto` — Adjunto RS
- `POS_rsi` — Responsable de Seguridad de la Información *(no existe hoy)*
- `POS_it` — Administrador de Sistemas (IT)

### Operaciones de vuelo (AOC)
- `POS_rov` — Responsable de Operaciones de Vuelo
- `POS_dispatcher` — Flight Dispatcher *(no existe hoy)*
- `POS_rot` — Responsable de Operaciones en Tierra
- `POS_pic` — Piloto Comandante
- `POS_sic` — Piloto Copiloto
- `POS_piloto_campania` — Piloto Campaña
- `POS_piloto_externo` — Piloto Externo / Colaborador

### CAMO
- `POS_camo_resp` — Responsable CAMO
- `POS_camo_planificacion` — Responsable de Planificación e Ingeniería
- `POS_camo_registros` — Responsable de Gestión de Datos / Registros (Parte-IS) *(no existe hoy)*
- `POS_camo_tecnico` — Técnico CAMO

### Parte-145
- `POS_145_resp` — Responsable de Parte-145 (Certificador CRS)
- `POS_145_mantenimiento` — Responsable de Mantenimiento (Línea/Base)
- `POS_mecanico_b` — Mecánico Certificado (B1/B2)
- `POS_mecanico_ayudante` — Mecánico Ayudante / Apoyo

### Organización de formación (ATO)
- `POS_ht` — Jefe de Enseñanza
- `POS_fi_tri` — Instructor de Vuelo (FI/TRI)
- `POS_ground_instructor` — Instructor de Teoría
- `POS_ato_admin` — Responsable de Administración (ATO)

### Almacén y logística
- `POS_almacen_resp` — Responsable de Almacén
- `POS_logistica_tecnico` — Técnico de Logística
- `POS_almacen_operario` — Operario de Almacén

### Administrativo y financiero
- `POS_admin_rrhh` — Responsable de Administración y RRHH
- `POS_contabilidad_resp` — Responsable de Contabilidad
- `POS_contabilidad_aux` — Auxiliar Contable

### Comercial
- `POS_comercial_resp` — Responsable Comercial
- `POS_comercial_senior` — Comercial Senior
- `POS_comercial_junior` — Comercial Junior

### Lo que del organigrama NO se convierte en puesto

- **Alumno Piloto** — no es un puesto. Es una persona con expediente formativo y sin casilla.
  Ver eje SUJETO. Afecta a 83 usuarios.
- **Comité Transversal de Seguridad (SMS/SGSI)** — es un órgano, no una posición. Sus miembros
  ocupan sus propios puestos (RS, RSI, DR, RCC). Si hace falta trazar quién lo compone, es un
  dato, no un grupo.

### Puestos que existen en el ERP y NO están en el organigrama

Necesitan una decisión explícita antes de implementar:

- **Propietario de Helicóptero** (`RPropietario_helicoptero`, 2 usuarios)
- **Trabajador Externo** (`RTExterno_base`, 4 usuarios)
- **Comercial Externo** (aparece en `roles_2026.xml`, sin grupo legacy)

---

## 3. Catálogo del eje CAPACIDAD

Regla de construcción: **se conserva el xmlid, se cambia el nombre visible.** Las 299
referencias `groups=` de las vistas apuntan al xmlid y no se tocan.

Categoría Odoo propuesta: **"Capacidad (permisos)"**, oculta a los administradores funcionales.

### 3.1 Capacidades que ya existen (renombrado)

**Transversales**
- `leulit.RBase` → *Acceso base al ERP*
- `leulit.RBase_employee` → *Personal interno*
- `leulit.RBase_hide` → **revisar qué protege antes de renombrar**
- `leulit.RDocumentos_responsable` → *Documentos: borrar*
- `leulit_esignature.RE_base` → *Firma electrónica*
- `leulit.leulit_user_checklist` → *Checklist: usar*
- `leulit.leulit_manager_checklist` → *Checklist: gestionar*

**Vuelo y operaciones**
- `leulit.ROperaciones_piloto_externo` → *Vuelo: registrar el propio*
- `leulit.ROperaciones_alumno` → **se elimina**; su función pasa a *Formación: expediente propio*
- `leulit.ROperaciones_operador` → *Vuelo: operar como especialista*
- `leulit.ROperaciones_piloto` → *Vuelo: operar*
- `leulit.ROperaciones_responsable` → *Vuelo: supervisar*
- `leulit.ROperaciones_gestor` → *Vuelo: administrar*
- `leulit.ROperaciones_parte_privado` → *Parte de piloto privado*
- `leulit.RCampaña_operador` → *Campaña: operar*
- `leulit.RCampaña_piloto` → *Campaña: pilotar*
- `leulit_actividad.RActividad_user` → *Actividad: registrar*
- `leulit_actividad.RActividad_gestor` → *Actividad: gestionar*
- `leulit.RPropietario_helicoptero` → *Propietario: ver su flota*

**Planificación**
- `leulit_planificacion.RPlanificacion_own` → *Planificación: la propia*
- `leulit_planificacion.RPlanificacion_all` → *Planificación: ver toda*
- `leulit_planificacion.RPlanificacion_manager` → *Planificación: gestionar*
- `leulit_planificacion.RPlanificacion_planner` → *Planificación: planificar*

**Mantenimiento, CAMO y almacén**
- `leulit.RTaller_base` → *Taller: ejecutar*
- `leulit.RTaller_responsable` → *Taller: supervisar*
- `leulit_parte_145.RM145_base` → *Parte-145: cumplimentar*
- `leulit.RCAMO_base` → *CAMO: gestionar*
- `leulit_almacen.RBase_almacen` → *Almacén: operar*
- `leulit_almacen.RResponsable_almacen` → *Almacén: gestionar*

**Formación**
- `leulit_escuela.REscuela_base` → *Formación: expediente propio*
- `leulit_escuela.REscuela_responsable` → *Formación: gestionar*

**Calidad y seguridad**
- `leulit.RCalidad_base` → *Calidad: gestionar*
- `leulit_seguridad.RSeguridad_user` → *SMS: reportar*
- `leulit_seguridad.RSeguridad_responsable` → *SMS: gestionar*

**Comercial y administración**
- `leulit.RComercial_base` → *Comercial: operar*
- `leulit.RComercial_responsable` → *Comercial: gestionar*
- `leulit_crm_team.group_sale_salesman_team` → *Comercial: ver documentos de mi equipo*
- `leulit.RContabilidad_Adjunto_base` → *Contabilidad: auxiliar*

**Tareas**
- `leulit_tarea.RT_base` → *Tareas: las propias*
- `leulit_tarea.RT_administrador` → *Tareas: administrar*
- `leulit_tarea.RT_gestor` → *Tareas: gestionar*
- `leulit_tarea.RT_proyectos_tareas_administrador` → *Tareas: administrar etapas*

**Externos**
- `leulit_trabajador_externo.RTExterno_base` → *Trabajador externo*
- `leulit_trabajador_externo.RTExterno_gestor` → *Trabajador externo: gestionar*

**IT y sistema**
- `leulit.RolIT_predev` → *IT: soporte*
- `leulit.RolIT_developer` → *IT: desarrollo*
- `leulit.RMigracion_responsable` → **revisar si sigue vivo**
- `leulit_groups_manager.group_groups_manager` → *IT: gestión de grupos*
- `leulit_user_impersonate.group_impersonate_user` → *IT: suplantar usuario*

### 3.2 Capacidades nuevas

No existen hoy y son las que sostienen la parte de auditoría del organigrama:

- `CAP_formacion_impartir` — dar clase, evaluar, firmar partes como instructor.
  Hoy no se distingue de *Formación: gestionar*.
- `CAP_formacion_auditar` — leer **todos** los expedientes formativos en solo lectura.
  **Es la que pide un auditor y hoy no existe en ninguna forma.**
- `CAP_sms_auditar` — leer todo el SMS en solo lectura sin poder gestionarlo.
- `CAP_auditoria_interna` — lectura transversal de todos los módulos, sin escritura.
  Soporta el puesto *Auditor Interno*.
- `CAP_registros_partis` — gestión de registros y datos bajo Parte-IS.
- `CAP_dispatch` — planificación y control de despacho de vuelo, separada de *Vuelo: administrar*.

### 3.3 Huecos detectados

No hay grupo propio de **Contabilidad titular** ni de **RRHH**: ese permiso hoy lo dan los
grupos estándar de Odoo (`account.*`, `hr.*`). Los puestos `POS_contabilidad_resp` y
`POS_admin_rrhh` compondrán grupos estándar directamente. **Decidir si se envuelven en una
capacidad propia** por coherencia con el resto del catálogo.

---

## 4. Matriz PUESTO → CAPACIDADES

Todo puesto incluye, salvo indicación contraria: *Acceso base al ERP*, *Personal interno*,
*Formación: expediente propio*, *SMS: reportar*, *Tareas: las propias*, *Planificación: la propia*.
Se abrevia como **[base]**.

### Dirección y conformidad

**`POS_dr` — Director Responsable**
[base] + todas las capacidades. Se implementa heredando el resto de puestos, como ya hacía
`roles_2026.xml` con `role_dr`.

**`POS_rcc` — Responsable de Control de Conformidad**
[base] + *Calidad: gestionar*, `CAP_auditoria_interna`, `CAP_formacion_auditar`,
`CAP_sms_auditar`, *Documentos: borrar*.
Lectura transversal; **sin** capacidades de gestión operativa (ver §7).

**`POS_rcc_adjunto` — Adjunto RCC**
Idénticas a `POS_rcc` salvo *Documentos: borrar*.

**`POS_auditor_interno` — Auditor Interno**
[base] + `CAP_auditoria_interna`, `CAP_formacion_auditar`, `CAP_sms_auditar`.
**Solo lectura. Ninguna capacidad de escritura, en ningún módulo.**

**`POS_rs` — Responsable de Seguridad Operacional**
[base] + *SMS: gestionar*, `CAP_sms_auditar`.

**`POS_rs_adjunto` — Adjunto RS**
[base] + *SMS: gestionar*.

**`POS_rsi` — Responsable de Seguridad de la Información**
[base] + `CAP_registros_partis`, `CAP_auditoria_interna`.

**`POS_it` — Administrador de Sistemas**
[base] + *IT: soporte*, *IT: desarrollo*, *IT: gestión de grupos*, *IT: suplantar usuario*.

### Operaciones de vuelo

**`POS_rov` — Responsable de Operaciones de Vuelo**
[base] + *Vuelo: administrar* (que arrastra supervisar/operar), *Actividad: gestionar*,
*Planificación: gestionar*, *Planificación: ver toda*.

**`POS_dispatcher` — Flight Dispatcher**
[base] + `CAP_dispatch`, *Planificación: planificar*, *Planificación: ver toda*, *Vuelo: supervisar*.

**`POS_rot` — Responsable de Operaciones en Tierra**
[base] + *Vuelo: supervisar*, *Actividad: gestionar*, *Planificación: ver toda*.

**`POS_pic` y `POS_sic` — Piloto Comandante y Copiloto**
[base] + *Vuelo: operar*, *Actividad: registrar*, *Firma electrónica*.
**Capacidades idénticas.** Quién es comandante y quién copiloto lo decide `PV_*` en cada vuelo.
Los dos puestos existen para el organigrama y la auditoría, no para los permisos.

**`POS_piloto_campania` — Piloto Campaña**
[base] + *Vuelo: operar*, *Campaña: pilotar* (que arrastra *Campaña: operar*),
*Actividad: registrar*, *Firma electrónica*.

**`POS_piloto_externo` — Piloto Externo / Colaborador**
*Acceso base al ERP* + *Vuelo: registrar el propio*, *Parte de piloto privado*, *Firma electrónica*.
**Sin *Personal interno*.** Alcance limitado por `ir.rule` a sus propios vuelos.

### CAMO

**`POS_camo_resp` — Responsable CAMO**
[base] + *CAMO: gestionar*, *Taller: supervisar*, *Parte-145: cumplimentar*, *Planificación: ver toda*.

**`POS_camo_planificacion` — Responsable de Planificación e Ingeniería**
[base] + *CAMO: gestionar*, *Planificación: gestionar*.

**`POS_camo_registros` — Responsable de Gestión de Datos / Registros (Parte-IS)**
[base] + *CAMO: gestionar*, `CAP_registros_partis`, *Documentos: borrar*.

**`POS_camo_tecnico` — Técnico CAMO**
[base] + *CAMO: gestionar*.

### Parte-145

**`POS_145_resp` — Responsable de Parte-145 (Certificador CRS)**
[base] + *Taller: supervisar*, *Parte-145: cumplimentar*, *Almacén: operar*, *Firma electrónica*.

**`POS_145_mantenimiento` — Responsable de Mantenimiento (Línea/Base)**
[base] + *Taller: supervisar*, *Parte-145: cumplimentar*, *Almacén: operar*.

**`POS_mecanico_b` — Mecánico Certificado (B1/B2)**
[base] + *Taller: ejecutar*, *Parte-145: cumplimentar*, *Almacén: operar*, *Firma electrónica*.

**`POS_mecanico_ayudante` — Mecánico Ayudante / Apoyo**
[base] + *Taller: ejecutar*, *Almacén: operar*.
**Sin** *Parte-145: cumplimentar* ni *Firma electrónica*.

### Formación (ATO)

**`POS_ht` — Jefe de Enseñanza**
[base] + *Formación: gestionar*, `CAP_formacion_impartir`, `CAP_formacion_auditar`,
*Vuelo: supervisar*, *Planificación: ver toda*.

**`POS_fi_tri` — Instructor de Vuelo**
[base] + `CAP_formacion_impartir`, *Vuelo: operar*, *Actividad: registrar*, *Firma electrónica*.

**`POS_ground_instructor` — Instructor de Teoría**
[base] + `CAP_formacion_impartir`.
**Sin** capacidades de vuelo.

**`POS_ato_admin` — Responsable de Administración (ATO)**
[base] + *Formación: gestionar*, *Planificación: gestionar*.

### Almacén

**`POS_almacen_resp` — Responsable de Almacén**
[base] + *Almacén: gestionar* (arrastra operar), *Comercial: operar* (compras).

**`POS_logistica_tecnico` — Técnico de Logística**
[base] + *Almacén: operar*.

**`POS_almacen_operario` — Operario de Almacén**
[base] + *Almacén: operar*.
Idéntico al anterior en capacidades; se separa por organigrama. **Revisar con Almacén si
la recepción y el picking deben distinguirse de la gestión de stock.**

### Administración y comercial

**`POS_admin_rrhh` — Responsable de Administración y RRHH**
[base] + grupos estándar `hr.*`, *Tareas: gestionar*, *Trabajador externo: gestionar*.

**`POS_contabilidad_resp` — Responsable de Contabilidad**
[base] + grupos estándar `account.*`.

**`POS_contabilidad_aux` — Auxiliar Contable**
[base] + *Contabilidad: auxiliar*.

**`POS_comercial_resp` — Responsable Comercial**
[base] + *Comercial: gestionar* (arrastra operar), *Comercial: ver documentos de mi equipo*.

**`POS_comercial_senior` y `POS_comercial_junior`**
[base] + *Comercial: operar*, *Comercial: ver documentos de mi equipo*.
**Capacidades idénticas.** La diferencia es de organigrama y de RRHH, no de ERP.

### Sin puesto: alumno externo

No es un puesto y no lleva grupo de organigrama.
*Acceso base al ERP* + *Formación: expediente propio* + *Tareas: las propias* +
*Planificación: la propia* + *Firma electrónica*.
**Sin *Personal interno*.** Todo su alcance lo fijan las `ir.rule` del §5.

---

## 5. Eje SUJETO — reglas `ir.rule` a escribir

Es la parte que hoy no existe: **9 reglas en todo el ERP**. Sin esto, el resto del documento
sigue siendo visibilidad de menús.

Patrón: la regla concede el registro cuando el usuario **es protagonista** de él, y se combina
con una regla sin grupo para el filtro de compañía.

### 5.1 Alcance personal

- `leulit.perfil_formacion` — visible si `alumno.partner_id = user.partner_id` o
  `piloto.partner_id = user.partner_id`. Excepción de lectura total para `CAP_formacion_auditar`
  y *Formación: gestionar*.
- `leulit.parte_escuela` y `leulit.rel_parte_escuela_cursos_alumnos` — visible si el usuario es
  el alumno o el instructor del parte.
- `leulit.rel_alumno_evaluacion` — visible si el usuario es el alumno evaluado.
- `project.task` — el alumno externo ve solo las tareas que tiene asignadas.
- `ir.attachment` — un adjunto es visible si lo es el registro del que cuelga.
  **Cuidado:** `leulit/models/ir_attachment.py` ya sobreescribe `check()` para dar acceso a
  adjuntos huérfanos a `RBase`. Hay que revisar la interacción antes de añadir reglas.
- `leulit.vuelo` — el piloto externo ve solo los vuelos en los que participa.

### 5.2 Excepciones de auditoría

Por el efecto documentado en `CLAUDE.md`: casi todos los roles encadenan hasta `RBase`, así que
**toda regla restrictiva sobre `RBase` alcanza también a los privilegiados**. Cada regla del §5.1
necesita su contrapartida `domain_force="[(1,'=',1)]"` para `CAP_auditoria_interna`,
`CAP_formacion_auditar` y `CAP_sms_auditar`.

### 5.3 Prohibido tocar

**No añadir reglas de fila sobre `hr.employee`.** `CLAUDE.md` documenta el intento del
2026-09-02 (`e85e8f1a`): rompió calendarios y roster para los pilotos en horas y se revirtió.
`hr.employee` se usa como catálogo de personal en todo el ERP.

---

## 6. Multicompañía

Decisión tomada: **puesto global, alcance por compañía.**

`res.groups` en Odoo no tiene compañía: un grupo es global. El alcance lo dan `company_ids`
del usuario y las `ir.rule` que filtran `company_id`.

**Limitación asumida y que hay que dejar por escrito:** quien sea Responsable de Almacén en
Icarus y comercial en Helipistas será Responsable de Almacén en las dos. Lo único que lo
contiene son los registros que ve. Afecta a los **21 usuarios multicompañía**.

Si esa limitación resulta inaceptable en Almacén o Parte-145 —que es donde vive Icarus— la
salida es desdoblar **solo esos** puestos (`POS_almacen_resp_icarus` / `_helipistas`), no
desdoblar el catálogo entero.

Precedente en el repo: `369ad3ec fix(parte_privado): acotar allowed_company_ids al entorno del piloto`.

---

## 7. Segregación de funciones

Decisión tomada: **matriz documentada, sin bloqueo en el ERP.** No se implementa ninguna
restricción; se deja constancia escrita.

Combinaciones a revisar por el RCC:

- `POS_rcc` / `POS_rcc_adjunto` / `POS_auditor_interno` **con** cualquier puesto operativo
  (ROV, ROT, Resp. CAMO, Resp. 145, HT). Un responsable de conformidad auditando su propio
  departamento es el hallazgo clásico.
- `POS_auditor_interno` **con** cualquier capacidad de escritura. Por diseño el puesto es de
  solo lectura; si alguien lo acumula con un puesto operativo, la lectura deja de ser
  independiente.
- `POS_145_resp` (certificador CRS) **con** `POS_almacen_resp`. Quien certifica la aeronavegabilidad
  y quien controla el material no deberían coincidir.
- `POS_contabilidad_resp` **con** `POS_contabilidad_aux` o con `POS_comercial_resp`.

**`POS_dr` es la excepción permanente.** En una organización de este tamaño el Director
Responsable acumula puestos de forma legítima. Es la razón principal para documentar y no
bloquear: cualquier constraint tendría que exceptuarlo siempre.

*Esta lista es una propuesta de partida elaborada desde el organigrama, no una lectura
reglamentaria. La valida el RCC.*

---

## 8. Plan de implantación

### Fase 1 — Aditiva, sin parada, nadie nota nada

1. Arreglar `leulit_escuela/models/leulit_alumno.py:493-530` (`alta_alumno`):
   resolver los grupos por **xmlid** en vez de por nombre; **no crear `leulit.piloto`** salvo
   que la persona vaya a volar; dejar de hardcodear `company_id = 1`.
   **Es requisito previo al renombrado**: es el único código que rompería.
2. Crear los 36 grupos `POS_*` en una categoría nueva.
3. Renombrar las capacidades (solo `<field name="name">`; los xmlid no se tocan).
4. Crear las 6 capacidades nuevas del §3.2.
5. Asignar puesto a las ~40 personas de plantilla.
   Los 83 alumnos externos y los ~12 externos varios **no llevan puesto**.

La cadena `implied_ids` de Operaciones sigue **intacta**. Nadie pierde ni gana acceso.

```bash
./upd_module.sh leulit dev
./upd_module.sh leulit_escuela dev    # lleva el cambio de alta_alumno
```

### Fase 2 — Verificación en frío

Script que calcula, para los 135 usuarios, el conjunto **efectivo** de grupos (incluidos los
heredados) antes y después, y produce el diff. **No se corta nada hasta que ese diff esté
explicado usuario por usuario.**

Es el paso que distingue esta migración de un big-bang: los errores se descubren aquí, no el
lunes con la gente dentro.

### Fase 3 — El corte, en ventana

Romper la cadena `piloto_externo -> alumno -> operador -> piloto -> responsable -> gestor`.
Los puestos ya componen explícitamente lo que la cadena heredaba.

Requiere ventana fuera de horario aunque no haya cambio de esquema en base de datos: los
permisos cambian bajo los pies de quien está dentro (un parte a medias puede dar `AccessError`
al guardar) y los grupos van cacheados en sesión.

```bash
./upd_module.sh leulit prod
```

### Fase 4 — Lo que hoy no existe

Escribir las `ir.rule` del §5 y activar las capacidades de auditoría. Es la fase que convierte
esto en control de acceso real y no en visibilidad de menús. Puede ir por módulos.

### Fase 5 — Limpieza

- Borrar `addons/leulit/roles_2026.xml` (26 grupos, 0 usos, comentado desde julio).
- Borrar `ROL_*` de `addons/leulit/utilitylib.py:28-36` (9 constantes, 0 usos).
- Revisar y cerrar las 25 cuentas dormidas de más de un año, y las 44 de más de seis meses.
- Definir política de baja automática por inactividad.

---

## 9. Decisiones pendientes

Hay que resolverlas antes de implementar la Fase 1:

1. **Jerarquía de pilotos.** En el organigrama, PIC, SIC, Piloto Campaña y Piloto Externo
   cuelgan del **ROT** (Operaciones en Tierra), no del **ROV**. ¿Es intencionado o es un
   artefacto de formato? Afecta a quién supervisa a quién.
2. **Los tres puestos del ERP que no están en el organigrama**: Propietario de Helicóptero,
   Trabajador Externo, Comercial Externo. ¿Entran en el catálogo o se retiran?
3. **`RBase_hide` y `RMigracion_responsable`**: hay que averiguar qué protegen antes de
   renombrarlos o retirarlos.
4. **Contabilidad y RRHH**: ¿se envuelven los grupos estándar de Odoo en capacidades propias
   por coherencia, o los puestos los componen directamente?
5. **Operario de Almacén vs Técnico de Logística**: hoy tendrían capacidades idénticas.
   ¿Deben distinguirse recepción/picking de la gestión de stock?
6. **Alcance de `CAP_auditoria_interna`**: ¿lectura de *todo*, incluidos datos de RRHH y
   contabilidad, o acotada a los módulos operativos?

---

## 10. Fuera de alcance pero detectado

**Credenciales en claro y versionadas.** `docker/docker-compose.yml` y
`dockerserver/docker-compose.yml` (producción) contienen las mismas credenciales, en claro y
trackeadas en git: `POSTGRES_PASSWORD`, `N8N_ENCRYPTION_KEY`, `N8N_BASIC_AUTH_PASSWORD`,
`MB_DB_PASS`. Rotarlas requiere parada, y re-cifrar las credenciales guardadas dentro de n8n.
No forma parte de este trabajo, pero convive con él en cualquier revisión de accesos.
