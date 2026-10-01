# KPIs AESA (Metabase) — qué mide cada indicador y de dónde sale el dato

Documento pensado para quien consulta el dashboard sin conocimientos técnicos: qué
significa cada número y de qué información del ERP sale, sin código.

Dashboard: **"Dashboard KPIs AESA"**, colección **"KPI AESA"** en Metabase
(`https://metabase.helipistas.com`). Todos los indicadores leen directamente de la
base de datos del ERP en producción (`productiu`) — no hay hojas de cálculo ni carga
manual de por medio. Cada vez que se abre el dashboard, se recalculan con los datos
del momento.

El dashboard está organizado en 7 bloques (2.1 a 2.7), cada uno con su propia carpeta
en Metabase. Este documento repasa los 7, con más detalle en el **2.2** y el **2.4**,
que son los que se han pedido expresamente.

---

## Una idea previa: qué es una "ocurrencia" en el ERP

La mayoría de estos indicadores (2.2, 2.4 y 2.7) se basan en el mismo sitio del ERP:
el registro de **ocurrencias / no conformidades** (ficha interna: `mgmtsystem.nonconformity`).
Ahí se apunta cualquier evento de seguridad o calidad que se detecta — desde algo que
reporta un piloto, hasta un hallazgo de una auditoría interna. Cada ocurrencia tiene
tres datos clave que los KPIs usan para filtrar y agrupar:

- **Origen**: cómo llegó al sistema — "Notificación interna" (lo reporta el propio
  personal), "Auditoría interna", "SNS (AESA)" (se ha enviado formalmente a AESA a
  través del Sistema de Notificación de Sucesos), etc.
- **Clasificación**: la gravedad — Generalidades, Significante o SNS.
- **Causa**: por qué ha ocurrido (opcional), p. ej. "Recurso humano no disponible o
  inadecuado".

Con esos tres campos se construyen la mayoría de los indicadores de seguridad
operacional del dashboard.

---

## 2.1 · Mejora de la seguridad

**Circulares de seguridad operacional realizadas** — cuenta, año a año, cuántas
circulares de seguridad operacional se han emitido. Sale del registro de circulares
del ERP, contando solo las marcadas como "seguridad operacional" (hay otros tipos de
circular que no cuentan aquí).

## 2.2 · Cumplimiento normativo

Este bloque tiene dos gráficas:

**No conformidades por área y año** — cuenta las ocurrencias que se detectaron en una
**auditoría interna** y que tienen gravedad Significante o SNS (se excluyen las de
Generalidades), agrupadas por el área del sistema de gestión a la que pertenecen y por
año.

**Reportes SNS (AESA)** — <https://metabase.helipistas.com/question/129-reportes-sns-aesa>

Es el indicador pedido. Mide **cuántas ocurrencias se han reportado formalmente a AESA
a través del Sistema de Notificación de Sucesos (SNS)**, año a año.

Cómo se obtiene: de todas las ocurrencias registradas en el ERP, se cuentan solo las
que tienen marcado como **origen "SNS (AESA)"** — es decir, las que el departamento de
seguridad ha identificado explícitamente como enviadas al regulador, no todas las
ocurrencias internas. Se agrupan por el año en que se creó el registro en el ERP (no
por la fecha real del suceso, que puede ser anterior).

En corto: es un recuento directo — "¿a cuántas ocurrencias les hemos puesto la
etiqueta de que se enviaron a AESA, cada año?".

## 2.3 · Gestión del cambio

**Gestiones del cambio realizadas** — cuenta, por año, las "Gestiones del Cambio"
(proyectos identificados en el ERP con el código "GC-") que se han abierto, sea cual
sea su estado actual (en curso, cerradas, etc.). Sale del módulo de proyectos.

## 2.4 · Cultura de seguridad

**Ocurrencias recibidas al año** — <https://metabase.helipistas.com/question/131-ocurrencias-recibidas-al-ano>

Es el otro indicador pedido. Mide **cuántas ocurrencias reporta directamente el
personal** cada año (no las que salen de una auditoría ni de otra vía), como termómetro
de si la gente está usando el canal de notificación voluntaria — de ahí que esté bajo
"cultura de seguridad".

Cómo se obtiene: se cuentan las ocurrencias cuyo **origen es "Notificación interna"**,
agrupadas por año y por su clasificación de gravedad (Generalidades, Significante o
SNS), así que en la gráfica se ve tanto el volumen total como su reparto por gravedad.

## 2.5 · Responsabilidad primaria

**% de personal formado en gestión de la seguridad** — compara, a fecha de hoy, el
total de empleados activos en el ERP con cuántos de ellos han completado **este año**
el curso "Entrenamiento en Seguridad Operacional SMS" (según su ficha de formación en
el módulo de escuela/RRHH). El resultado es el porcentaje de plantilla formada.

## 2.6 · Seguridad de la información (SGSI)

**% de usuarios con acceso al sistema que han firmado las políticas** — para cada año,
hace una "foto" a 31 de diciembre: cuántos usuarios internos activos tenía el ERP dados
de alta hasta esa fecha, y de esos, cuántos ya tenían firmada la política de seguridad
de la información (NDA). La línea muestra el % firmado.

> Limitación conocida (indicada en la propia ficha de Metabase): si un usuario se ha
> dado de baja del ERP, no se cuenta en ningún año — no hay histórico de bajas, solo
> del estado actual.

## 2.7 · Recursos adecuados

**Ocurrencias por recurso inadecuado o no disponible** — cuenta, por año, las
ocurrencias a las que se les ha asignado la causa "Recurso humano no disponible o
inadecuado" dentro de su análisis. Sirve para ver si la falta de recursos está detrás
de los incidentes.

---

## Detalle: qué ocurrencias concretas entran en cada bloque

Consulta hecha directamente sobre la base de datos el 2026-09-23. Los cuatro
apartados que se basan en "ocurrencias" (2.2 dos veces, 2.4 y 2.7) — los demás (2.1,
2.3, 2.5, 2.6) no usan este registro, ver sus secciones arriba.

### 2.2 · Reportes SNS (AESA) — 16 ocurrencias

Todas las que tienen el origen "SNS (AESA)" marcado, de más antigua a más reciente:

- 2022-11-24 — Fallo de Governor
- 2023-01-17 — Grieta en el windshield izquierdo del EC120
- 2023-02-17 — ANO-0000447 (indicación del dual tacómetro cae a 0)
- 2023-03-13 — Vibración inusual en el cíclico
- 2024-02-15 — Proximidad con tráfico en la zona de Olesa de Montserrat
- 2024-03-04 — PVC2023-D7 (incumplimiento M.A.503, control de componentes con vida límite)
- 2024-05-15 — Suceso incendio Batea
- 2024-10-31 — Incidente aeropuerto Valencia
- 2025-07-08 — Autorización de aterrizaje en Sabadell
- 2025-10-24 — Crack found on PILOT CYCLIC BASE
- 2026-02-19 — Fallo de comunicaciones
- 2026-02-20 — ELT SE-JXP
- 2026-06-19 — Incursión en ATZ
- 2026-06-22 — Incidente EXECHHT *(clasificada como "Generalidades", no "SNS")*
- 2026-08-06 — Tapón de cuba de combustible abierto con lluvia
- 2026-09-17 — Correu d'incidències sense resposta *(clasificada como "Generalidades", no "SNS")*

> Nota de calidad del dato: el indicador cuenta por el **origen** marcado ("SNS
> (AESA)"), no por la clasificación de gravedad. Dos de las 16 están clasificadas
> internamente como "Generalidades" — probablemente el origen se marcó pero la
> clasificación de gravedad no se actualizó, o al revés. Si se quiere que el KPI
> refleje solo sucesos realmente enviados a AESA, merece la pena revisar esas dos
> fichas.

### 2.2 · No conformidades por área y año (detección en auditoría interna) — 31 ocurrencias

Todas "Significante" (ninguna "SNS" en este grupo). Por área, de más antigua a más
reciente: 12 en **Conformidad**, 4 en **Parte 145**, 3 en **OPERACIONES** (común a
ATO/AOC/NCO/LCI/SPO), 2 en **ATO**, 2 en **CAMO**, 1 en **Departamento IT**, 1 en
**LCI**. Detalle completo consultable en Metabase, pregunta 128, o filtrando en el
ERP por origen = "Auditoría interna" y clasificación ≠ "Generalidades".

### 2.4 · Ocurrencias recibidas al año (notificación interna) — 851 ocurrencias

Demasiadas para listar una a una aquí; el propio gráfico 2.4 ya las desglosa por año
y gravedad. Resumen:

- 2022: 73 (todas Generalidades)
- 2023: 323 (todas Generalidades)
- 2024: 160 (todas Generalidades)
- 2025: 165 (163 Generalidades + 2 SNS)
- 2026 (hasta el 2026-09-23): 130 (126 Generalidades + 4 SNS)

No hay ninguna clasificada como "Significante" en este grupo — encaja con que lo
"Significante" suele salir de auditoría (ver 2.2) o de un reclasificado posterior, no
de la notificación inicial del personal. Si hace falta el listado completo (851
filas), se puede exportar desde Metabase (pregunta 131 → "Ver tabla" → descargar CSV)
o pedirlo aquí y se genera un fichero aparte.

### 2.7 · Ocurrencias por recurso inadecuado o no disponible — 3 ocurrencias

- 2025-11-25 — Helicópteros no preparados (servicio de AOC, varias aeronaves no
  estaban listas)
- 2026-02-15 — Desmontar doble mando (el mecánico de guardia del fin de semana no
  sabía desmontar el doble mando del Colibrí)
- 2026-08-20 — Clases programadas no realizadas (de 5 sesiones de RT programadas en
  agosto, solo se dieron 2)

---

## Dónde verlo

Dashboard completo: colección **KPI AESA** en Metabase (id 29), pregunta a pregunta:
`https://metabase.helipistas.com/dashboard/9`. Cada gráfica se puede abrir por
separado para ver la tabla de datos que hay detrás (botón de la gráfica → "Editar
pregunta" o "Ver tabla").
