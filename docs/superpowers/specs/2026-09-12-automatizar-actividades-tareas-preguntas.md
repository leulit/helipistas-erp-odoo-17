# Automatizar actividades al asignar responsable — preguntas para el equipo

Punto de partida: `Automatizar actividades en proyectos de Odoo.pdf` (export de un
chat de Gemini) propone, para Odoo **16** Community genérico, crear una
`base.automation` que al crear una `project.task` programe automáticamente una
actividad "por hacer" para el usuario responsable, con código Python escrito a
mano en la acción.

Ese documento describe un Odoo genérico de fábrica. Nuestro entorno es Odoo
**17** con `project.task` fuertemente customizado por varios módulos leulit, así
que antes de diseñar nada se ha contrastado contra el repo y contra producción
(vía MCP). Este documento recoge lo verificado y las decisiones que faltan por
tomar — no es todavía un diseño cerrado.

## Lo verificado en el repo y en producción

**No existe ninguna automatización de este tipo hoy.** Cero usos de
`base_automation` o `activity_schedule()` en todo `addons/leulit_*`. En
producción, el módulo `base_automation` está instalado pero solo tiene 2
reglas configuradas, ambas de recordatorios de auditoría
(`mgmtsystem.audit`), nada relacionado con tareas o acciones.

**`project.task` está muy lejos de ser genérico.** Lo heredan 4 módulos
(`leulit_tarea`, `leulit_actividad_taller`, `leulit_planificacion`,
`leulit_taller`) y arrastra campos propios de mantenimiento Part-145:
`job_card_id`, `maintenance_request_id`, `doble_check_ids`,
`security_inspection_ids`, `tipo_tarea_taller`, etc. El responsable se guarda
en `user_ids` (Many2many, "Assignees").

**`mgmtsystem.action` (módulo OCA vendorizado) es el otro modelo candidato.**
Su responsable es `user_id` (Many2one, un único usuario) — más simple que
`project.task`. Es el modelo con más actividades manuales abiertas ahora
mismo en producción: **107**, frente a **40** de `project.task`.

**Ya existe un precedente que trata ambos modelos como un par.**
`leulit_tarea/models/mail_activity.py` define
`_MODELOS_CON_FECHA_LIMITE = ('project.task', 'mgmtsystem.action')` y una
constraint: la fecha de vencimiento de una actividad no puede ser posterior a
la fecha límite del registro padre (tarea o acción). Cualquier actividad que
generemos automáticamente con la misma fecha que la tarea/acción respeta esta
regla sin tocarla.

**Ya existen tipos de actividad que parecen pensados para esto.** "Tarea por
hacer" (genérico, sin `res_model` fijado) y "Acción" (categoría `reminder`,
ya vinculado a `mgmtsystem.action`). Ninguno se usa hoy de forma automática.

**Cardinalidad de asignados en `project.task`.** Sobre una muestra de 500
tareas recientes con responsable, el 99,4% tiene un único usuario en
`user_ids`; solo 3 casos tenían 2 o 3 usuarios a la vez. Es un caso real pero
minoritario — hay que decidir qué hacer con él, no se puede ignorar sin más.

**Odoo 17 permite programar la "próxima actividad" de forma declarativa**,
sin Python a mano (a diferencia del código del PDF, que es de Odoo 16): la
acción de tipo `next_activity` en `ir.actions.server`/`base.automation` con
`activity_user_type` = específico / genérico (campo del propio registro) /
dinámico. Además existe un trigger nativo `on_user_set` ("User is set"),
pensado exactamente para "el campo responsable acaba de pasar de vacío a
tener valor" — no solo `on_create`.

## Decidido hasta ahora

- **Alcance inicial:** `project.task` y `mgmtsystem.action` juntos, mismo
  mecanismo, mismo módulo — siguiendo el precedente ya existente en
  `mail_activity.py`.
- **Módulo candidato:** `leulit_tarea`. Es el único módulo que ya trata estos
  dos modelos como un par transversal, y lo hace extendiendo `mail.activity`
  en vez de tocar el módulo OCA `mgmtsystem_action` directamente — mismo
  patrón que tendríamos que seguir aquí.

## Preguntas abiertas para el equipo

**1. ¿En qué momento se dispara la creación de la actividad?**
No es solo "al crear": en el flujo real (p.ej. kanban de taller) una tarea
puede nacer sin responsable y asignarse después. Opciones:
- Al asignar responsable (`on_user_set`) — cubre creación-ya-asignada y
  asignación posterior por igual.
- Solo al crear (`on_create`), como en el PDF original — si la tarea nace sin
  responsable y se asigna más tarde, no pasa nada.
- Ambos, más reasignación posterior (el responsable cambia una segunda vez)
  — esto obliga a lógica anti-duplicados explícita.

**2. ¿Qué pasa si el registro se crea sin responsable y nunca se asigna vía
el campo estándar (p.ej. se deja el trabajo en un pool de equipo)?** ¿No pasa
nada, o hay algún fallback (p.ej. asignar al creador, como hace el PDF)?

**3. ¿Qué fecha de vencimiento lleva la actividad si la tarea/acción no
tiene `date_deadline`?** El PDF pone "hoy" por defecto — eso puede generar
ruido/falsa urgencia en tareas que deliberadamente no tienen fecha. Alternativa:
dejar la actividad sin fecha límite.

**4. `project.task` con varios asignados (`user_ids` con 2+ usuarios,
~0,6% de los casos): ¿una actividad por cada uno, o solo para el primero?**
El PDF genera una por usuario; es el comportamiento más "correcto" pero hay
que confirmarlo porque no es el caso mayoritario.

**5. Anti-duplicados: si el registro ya tiene una actividad pendiente del
mismo tipo (p.ej. se reabre, se reasigna, o el cron/algún flujo dispara el
trigger dos veces), ¿se crea otra igual o se evita duplicar?** Relevante sobre
todo si la respuesta a la pregunta 1 incluye reasignaciones posteriores.

**6. ¿Aplica a TODAS las `project.task`/`mgmtsystem.action` sin excepción, o
solo a ciertos subtipos?** `project.task` se usa en varios contextos
(taller/Part-145, planificación, tareas internas genéricas vía
`leulit_tarea`). ¿Tiene sentido la actividad automática en los tres, o solo
en alguno?

**7. Mecanismo de implementación: ¿regla declarativa (`base.automation` +
`ir.actions.server` tipo `next_activity`, configurable desde XML como ya se
hace con los 19 `ir.cron` del repo) o código Python explícito (override de
`create`/`write`)?** La vía declarativa es más simple y sigue el patrón ya
usado en el repo, pero el caso de varios asignados (pregunta 4) y el
anti-duplicados (pregunta 5) no encajan bien en la configuración declarativa
estándar de Odoo — necesitarían Python de todas formas. Recomendación
preliminar: Python explícito en `leulit_tarea`, pero pendiente de cerrar tras
ver las respuestas a 1, 4 y 5.

**8. ¿La creación de la actividad debe notificar al usuario (comportamiento
estándar de `activity_schedule`, que añade un mensaje en el chatter y puede
generar notificación), o se quiere silenciosa?**

## Referencias técnicas (para quien implemente)

- `addons/leulit_tarea/models/mail_activity.py` — constraint de fecha límite
  ya existente sobre ambos modelos.
- `addons/leulit_tarea/models/project_task.py` — extensión actual de
  `project.task` en este módulo.
- Tipos de actividad existentes en producción: id 15 "Tarea por hacer"
  (genérico), id 18 "Acción" (`res_model` = `mgmtsystem.action`, categoría
  `reminder`).
- `mgmtsystem.action.user_id` (Many2one) vs `project.task.user_ids`
  (Many2many) — el punto de asimetría entre los dos modelos.
- Patrón de automatización declarativa ya usado en el repo para tareas
  periódicas: los 19 `ir.cron` bajo `addons/leulit_*/data/*.xml`.
