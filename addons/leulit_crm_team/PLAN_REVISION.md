# Revisión de código — `leulit_crm_team`

Revisión estática (sin entorno Odoo disponible: no se ha podido instalar/ejecutar el
módulo ni una BBDD real). Todas las afirmaciones están justificadas por lectura de
código de este módulo, del manifest, y de un grep dirigido al resto del repo (incluido
`third-party-addons/`) para detectar dependencias cruzadas.

Ficheros revisados (módulo completo, 7 ficheros):
`__init__.py`, `__manifest__.py`, `models/__init__.py`, `models/crm_lead.py`,
`security/crm_security_groups.xml`, `security/crm_security_rules.xml`, `README.md`.

## 1. Resumen ejecutivo

**7 hallazgos**: 2 críticos, 3 altos, 2 medios, 0 bajos (se documentan además 2
inconsistencias de documentación como notas, no contabilizadas como hallazgo de código).
Los dos críticos son bloqueantes: (a) el manifest promete una validación de "Perdido"
que no existe en ningún fichero Python/XML del módulo, y (b) hacer `medium_id`
obligatorio sin migración de datos puede tumbar la actualización del módulo si ya
existen leads con `medium_id` NULL en la BBDD (`productiu`). Los altos giran en torno al
mismo campo `medium_id` (rompe creación de leads en al menos un módulo ya instalado,
`helpdesk_mgmt_crm`) y a una regla `ir.rule` que no cubre el caso "lead sin asignar",
al contrario de lo que documenta el propio README del módulo.

## 2. Tabla de hallazgos

| Severidad | Fichero:línea | Problema | Escenario que lo dispara | Fix propuesto |
|---|---|---|---|---|
| Crítico | `__manifest__.py:13-14` | La descripción promete "obligar a usar el botón Perdido... garantizando motivo y nota de cierre", pero no existe ningún override de `action_set_lost`/`write`/vista que lo implemente | Cualquier usuario lee la descripción del módulo en Apps y asume que esa protección existe; un usuario marca un lead como perdido cambiando `probability=0` o `active=False` directamente (API, import, otro módulo) sin motivo | Implementar la validación (override Python + vista) o corregir la descripción del manifest para no prometer algo inexistente |
| Crítico | `models/crm_lead.py:8` | `medium_id` pasa a `required=True` sin `default` ni script de migración/backfill | Al actualizar el módulo (`./upd_module.sh leulit_crm_team dev --stop`) sobre una BBDD con leads existentes con `medium_id` NULL (caso muy probable en `productiu`), Odoo intenta `ALTER TABLE crm_lead ALTER COLUMN medium_id SET NOT NULL` y falla si hay NULLs, abortando la actualización | Añadir `default=` razonable (p.ej. un `utm.medium` "Desconocido") + script de migración `migrations/17.0.1.2.0/pre-migrate.py` que haga `UPDATE crm_lead SET medium_id=X WHERE medium_id IS NULL` antes del `_auto_init` |
| Alto | `models/crm_lead.py:8` | `required=True` rompe la creación de `crm.lead` en flujos que no informan `medium_id` | Confirmado en este repo: `addons/third-party-addons/helpdesk_mgmt_crm/wizard/helpdesk_ticket_create_lead.py:42` hace `self.env["crm.lead"].create(self._prepare_vals())` sin `medium_id` → `ValidationError`/`IntegrityError` al convertir un ticket de helpdesk en oportunidad. Muy probablemente también rompe la creación desde alias de correo (`message_new`) y el quick-create del Kanban de CRM (formulario reducido, sin el campo Medio visible) — esto no se puede confirmar sin entorno porque el código de `crm`/`mail` no está vendorizado en este repo | Añadir `default_medium_id` vía contexto en los wizards/flujos afectados, o mejor, dar un `default=` a nivel de campo en este módulo para no depender de que cada flujo externo lo informe |
| Alto | `security/crm_security_rules.xml:12-16` y `:32-36` | El dominio real `['\|', ('user_id','=',user.id), ('team_id.member_ids.user_id','=',user.id)]` NO incluye el caso `('user_id','=',False)` que el propio `README.md:101-121` documenta como parte del comportamiento esperado ("sin equipo asignado → debe verla") | Un lead/pedido sin `user_id` y sin ningún miembro del equipo del usuario asignado (p.ej. leads nuevos de la web aún sin repartir) se vuelve invisible para cualquier usuario con solo el grupo `group_sale_salesman_team`, contradiciendo la documentación y dejando leads "huérfanos" sin nadie que los vea/reparta | Añadir el tercer término OR: `['\|','\|', ('user_id','=',user.id), ('user_id','=',False), ('team_id.member_ids.user_id','=',user.id)]` en ambas reglas, si de verdad se quiere ese comportamiento (confirmar con el usuario, ver sección de dudas) |
| Alto | `models/crm_lead.py:8` | `ondelete='restrict'` sustituye el `ondelete='set null'` estándar de `utm.mixin` para `medium_id`, sin documentarlo en manifest/README | Un usuario intenta borrar un `utm.medium` (Configuración > Marketing > Medios) que esté referenciado por cualquier lead, incluso uno cerrado/perdido hace años → `IntegrityError` bloqueando el borrado en todo el sistema (no solo en este módulo), efecto no mencionado en ningún sitio | Si la intención es solo forzar que el campo esté relleno (integridad de datos nuevos), no cambiar `ondelete` — dejar el `set null` heredado, o si se cambia deliberadamente, documentarlo explícitamente y confirmarlo con el usuario |
| Medio | `security/crm_security_rules.xml:19,21` y `:39,41` | Ambas reglas conceden `perm_write=True` y `perm_unlink=True` sobre TODO registro que cumpla el dominio (propios + de todo el equipo), no solo lectura, pese a que el grupo se llama "Usuario: **Ver** documentos de mis equipos" | Un comercial del equipo "Taxi" sin más permisos puede editar o **borrar** (`unlink`) una oportunidad o un pedido de venta de un compañero de su mismo equipo, no solo verla | Confirmar con el usuario si el borrado/edición cruzada dentro del equipo es intencional; si no, separar `perm_unlink` (y quizá `perm_write`) en una regla/gruop distinto, más restrictivo |
| Medio | `README.md:108,119` vs `security/crm_security_rules.xml:12-16,32-36` | El README documenta el dominio usando `user.sale_team_ids.ids`, un campo que no existe como tal en `res.users` de Odoo estándar (la pertenencia a equipos se modela vía `crm.team.member`, no vía un campo plural `sale_team_ids` en `res.users`), y que además no es el dominio realmente implementado (`team_id.member_ids.user_id`) | Un mantenedor futuro lee el README, asume que ese es el dominio real/el campo existe, e introduce un bug al intentar reutilizar `user.sale_team_ids` en otra regla o vista | Corregir el README para que documente literalmente el dominio de `crm_security_rules.xml`, eliminando el ejemplo con el campo inexistente |

## 3. Hallazgos críticos/altos desarrollados

### 3.1 [CRÍTICO] Funcionalidad de "Perdido" prometida en el manifest pero no implementada

`__manifest__.py:7-15`:
```python
'description': """
    Añade un grupo de seguridad intermedio para CRM:
    - Usuario puede ver sus propios registros
    - Usuario puede ver registros de sus equipos de ventas
    - Usuario NO ve registros de otros equipos

    Además obliga a usar el botón "Perdido" para marcar leads como perdidos,
    garantizando que siempre se rellene el motivo y la nota de cierre.
""",
```

El módulo entero son 7 ficheros; el único fichero Python de modelo (`models/crm_lead.py`)
solo añade `medium_id`. No hay:
- override de `crm.lead.action_set_lost` (método estándar del wizard de "Perdido" en
  `crm`),
- override de `write()` que detecte `active=False`/`probability=0` y valide
  `lost_reason_id`,
- ninguna vista XML que oculte/bloquee el cambio directo de estado,
- ningún `@api.constrains`.

**Riesgo real**: cualquiera con acceso de escritura al lead (API externa, import,
otro módulo, o incluso el propio usuario editando el `kanban_state`/`probability`
desde la vista de lista) puede marcarlo como perdido sin motivo ni nota, exactamente
el escenario que el módulo dice impedir. Es una promesa de negocio (auditoría de
motivos de pérdida) que no se cumple.

**Fix propuesto** — dos alternativas, a decidir con el usuario (ver dudas):
1. Implementar la validación real, por ejemplo:
```python
class CrmLead(models.Model):
    _inherit = 'crm.lead'

    def write(self, vals):
        # Si se está desactivando/perdiendo el lead fuera del wizard estándar...
        closing = vals.get('active') is False or vals.get('probability') == 0
        if closing:
            for lead in self:
                if not (vals.get('lost_reason_id') or lead.lost_reason_id):
                    raise UserError(_(
                        "Debes indicar el motivo de pérdida usando el botón 'Perdido'."
                    ))
        return super().write(vals)
```
   (snippet ilustrativo, no verificado contra el comportamiento exacto de
   `action_set_lost` en Odoo 17 sin entorno — requiere pruebas reales antes de
   mergear).
2. O bien, si la funcionalidad nunca se llegó a implementar y no es prioritaria,
   corregir el manifest para que no describa algo inexistente.

### 3.2 [CRÍTICO] `medium_id` requerido sin migración de datos

`models/crm_lead.py:5-8`:
```python
class CrmLead(models.Model):
    _inherit = 'crm.lead'

    medium_id = fields.Many2one(required=True, ondelete='restrict')
```

`medium_id` es un campo heredado de `utm.mixin` (usado por `crm.lead`), normalmente
opcional (`ondelete='set null'`). Este módulo lo redeclara `required=True`.

Cuando Odoo actualiza un módulo, `BaseModel._auto_init()` compara la definición del
campo con la columna existente y, si pasa a `required=True`, intenta:
```sql
ALTER TABLE crm_lead ALTER COLUMN medium_id SET NOT NULL;
```
Si ya existe una sola fila con `medium_id IS NULL` (extremadamente probable en
`productiu`, dado que es un campo opcional en Odoo estándar y probablemente lleva
años sin rellenarse en todos los leads), ese `ALTER TABLE` falla y **la actualización
del módulo se aborta** — exactamente el tipo de `ERROR/CRITICAL` que `upd_module.sh`
está diseñado para detectar.

**Fix propuesto**: no declarar `required=True` a secas. Añadir un valor por defecto y,
sobre todo, un script de migración que rellene los NULL existentes antes del
`_auto_init`:
```python
# migrations/17.0.1.2.0/pre-migrate.py
def migrate(cr, version):
    cr.execute("""
        UPDATE crm_lead
           SET medium_id = (SELECT id FROM utm_medium WHERE name = 'Unknown' LIMIT 1)
         WHERE medium_id IS NULL
    """)
```
(el nombre exacto del medio "Unknown"/"Desconocido" y su xmlid deben confirmarse
contra el entorno real antes de aplicar — no verificable sin BBDD).

## 4. Plan de acción priorizado

1. **[Crítico]** Decidir con el usuario si la validación de "Perdido" se implementa
   ahora o se retira la frase del manifest (`__manifest__.py:13-14`) — no dejar
   documentado un comportamiento que no existe.
2. **[Crítico]** Antes de volver a lanzar `./upd_module.sh leulit_crm_team ... --stop`
   contra `productiu` o producción, comprobar cuántos `crm.lead` tienen
   `medium_id IS NULL` y decidir la estrategia de backfill/migración
   (`models/crm_lead.py:8`).
3. **[Alto]** Revisar todos los puntos de creación de `crm.lead` que no informan
   `medium_id` (confirmado: `helpdesk_mgmt_crm`; a confirmar en entorno real: alias de
   correo, quick-create de Kanban, formularios web) y decidir si se les da un
   `default_medium_id` vía contexto o si el propio campo lleva un `default=`.
4. **[Alto]** Confirmar si las reglas `ir.rule` deben incluir `user_id = False`
   (leads/pedidos sin asignar) tal como documenta el README, y corregir
   `security/crm_security_rules.xml:12-16,32-36` en consecuencia.
5. **[Alto]** Confirmar si el cambio de `ondelete='set null'` a `ondelete='restrict'`
   en `medium_id` es intencional; si no, revertirlo a `set null` (o no declarar
   `ondelete` y heredar el de `utm.mixin`).
6. **[Medio]** Confirmar si `perm_unlink=True`/`perm_write=True` sobre registros de
   compañeros de equipo es el comportamiento deseado para un grupo llamado "Ver
   documentos de mis equipos"; si no, separar los permisos.
7. **[Medio]** Corregir `README.md` para que el dominio documentado coincida
   literalmente con `security/crm_security_rules.xml` (eliminar la referencia a
   `user.sale_team_ids`, que no es un campo estándar de `res.users`).

## 5. Dudas / no verificable sin entorno

- **Quick-create de Kanban y formulario del lead**: no se puede confirmar sin abrir
  la vista real de `crm.lead` (heredada de `crm`, módulo no vendorizado en este repo)
  si el campo `medium_id` es visible en el formulario reducido de creación rápida.
  Si no lo es, `required=True` bloquea esa vía de creación con un error poco claro
  para el usuario final. Requiere prueba en el entorno Docker del usuario.
- **Alias de correo / `message_new`**: no se puede verificar en este repo si el flujo
  estándar de `crm.lead.message_new()` (creación de lead desde email entrante) informa
  `medium_id`; el código de `crm`/`mail` no está en este repo. Si no lo informa,
  `required=True` rompería también la captación de leads por email.
- **Estado de datos en `productiu`**: no se puede consultar cuántos `crm.lead`
  existentes tienen `medium_id NULL` sin acceso a la BBDD real; es el dato que decide
  si el hallazgo 3.2 se dispara literalmente en el próximo `-u`.
- **Semántica exacta del widget `selection_groups` para grupos sin `implied_ids`**:
  `group_sale_salesman_team` comparte `category_id` (`base.module_category_sales_sales`)
  con los grupos estándar de ventas pero deliberadamente no los hereda vía
  `implied_ids` (comentario explícito en `crm_security_groups.xml:13`). No he podido
  confirmar sin entorno si el formulario de Usuarios de Odoo 17 sigue mostrando este
  grupo como radio-button mutuamente excluyente junto a los grupos estándar, o si
  aparece como checkbox independiente (lo que permitiría a un usuario acumular este
  grupo además de "Todos los documentos", anulando la restricción vía OR de reglas).
  Requiere comprobación visual en la ficha de un usuario en el entorno de pruebas.
- **Motivo real de `ondelete='restrict'`**: no hay comentario ni commit message en el
  módulo que explique por qué se eligió `restrict` en vez de heredar `set null`; podría
  ser intencional (evitar perder trazabilidad del medio de origen) o un descuido. Se
  documenta como pregunta abierta en el plan de acción (punto 5) en vez de asumir.
