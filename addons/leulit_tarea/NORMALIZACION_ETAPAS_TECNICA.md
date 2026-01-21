# Normalización de Etapas - Documentación Técnica

## 📐 Arquitectura

### Modelos

#### 1. `leulit_tarea.unificar_etapas_wizard` (TransientModel)
Wizard principal de 3 pasos para normalización de etapas.

**Campos principales:**
```python
estado = fields.Selection([
    ('paso1', 'Selección'),
    ('paso2', 'Mapeo'),
    ('paso3', 'Simulación'),
])

modo_ejecucion = fields.Selection([
    ('simulacion', 'Simulación'),
    ('real', 'Ejecución Real'),
])

aplicar_a_proyectos = fields.Boolean()  # True = todos, False = específicos
proyecto_ids = fields.Many2many('project.project')
mapeo_linea_ids = fields.One2many('leulit_tarea.unificar_etapas_mapeo_linea')
crear_snapshot = fields.Boolean(default=True)
limpiar_etapas_obsoletas = fields.Boolean(default=False)
snapshot_id = fields.Many2one('leulit_tarea.unificar_etapas_snapshot')
etapas_eliminadas = fields.Integer(readonly=True)
```

#### 2. `leulit_tarea.unificar_etapas_mapeo_linea` (TransientModel)
Líneas de mapeo entre etapas origen y destino.

**Campos:**
```python
wizard_id = fields.Many2one('leulit_tarea.unificar_etapas_wizard')
etapa_origen_id = fields.Many2one('project.task.type')
etapa_destino_id = fields.Many2one('project.task.type')
proyectos_afectados = fields.Integer()
tareas_afectadas = fields.Integer()
```

#### 3. `leulit_tarea.unificar_etapas_snapshot` (Model)
Modelo persistente para guardar snapshots de rollback.

**Campos:**
```python
name = fields.Char()
fecha_snapshot = fields.Datetime()
user_id = fields.Many2one('res.users')
total_proyectos = fields.Integer()
total_tareas = fields.Integer()
estado_proyectos = fields.Text()  # JSON
estado_tareas = fields.Text()     # JSON
activo = fields.Boolean(default=True)
```

---

## 🔄 Flujo de Ejecución

### Diagrama de Estados

```
[Paso 1] → action_analizar_etapas() → [Paso 2] → action_simular_cambios() → [Paso 3]
                                                                                 ↓
                                                                    action_unificar_etapas()
                                                                                 ↓
                                                                   _limpiar_etapas_obsoletas() [OPCIONAL]
                                                                                 ↓
                                                                          [Completado]
```

### Métodos Principales

#### `action_analizar_etapas()`
**Propósito:** Analiza proyectos y crea mapeo de etapas

**Proceso:**
1. Obtiene proyectos según selección
2. Crea etapas destino si no existen (`_crear_etapas_destino`)
3. Obtiene etapas existentes (`_obtener_etapas_existentes`)
4. Genera líneas de mapeo con coincidencias automáticas
5. Transición a Paso 2

**Retorna:** Action para recargar vista en Paso 2

#### `action_simular_cambios()`
**Propósito:** Simula cambios sin aplicarlos

**Proceso:**
1. Valida mapeo
2. Ejecuta `_simular_normalizacion()`
3. Genera reporte detallado (`_generar_reporte_simulacion`)
4. Genera estadísticas (`_generar_stats_simulacion`)
5. Transición a Paso 3

**Retorna:** Action para recargar vista en Paso 3

#### `action_unificar_etapas()`
**Propósito:** Ejecuta normalización real

**Proceso:**
1. Valida modo ejecución (debe ser 'real')
2. Crea snapshot si está marcado (`_crear_snapshot`)
3. Normaliza proyectos (`_normalizar_proyecto`)
4. Normaliza tareas (`_normalizar_tareas`)
5. Muestra notificación con resultados

**Retorna:** Notificación de éxito

#### `_limpiar_etapas_obsoletas(etapas_destino, proyectos_procesados)` [NUEVO]
**Propósito:** Elimina etapas obsoletas sin uso después de normalizar

**Proceso:**
1. Obtiene todas las etapas del sistema
2. Identifica candidatas: todas - etapas destino
3. Para cada candidata verifica:
   - ¿Está en `project.project.type_ids`? → RETENER
   - ¿Está en `project.task.stage_id`? → RETENER
   - Si pasa ambas: ELIMINAR (sin uso)
4. Registra en logs: eliminadas y retenidas

**Parámetros:**
```python
etapas_destino: Recordset  # Etapas normalizadas a mantener
proyectos_procesados: Recordset  # Proyectos afectados (informativo)
```

**Retorna:** `int` - Cantidad de etapas eliminadas

**Seguridad:**
- Triple verificación antes de eliminar
- Logs detallados de cada decisión
- `try/except` para capturar errores de eliminación

---

## 🎯 Lógica de Negocio

### Diferencia Conceptual Crítica

```python
# ETAPAS DE PROYECTO (type_ids)
# Many2many - Etapas DISPONIBLES para el proyecto
proyecto.type_ids = [etapa1, etapa2, etapa3, ...]

# ETAPA DE TAREA (stage_id)
# Many2one - Etapa ACTUAL de la tarea
tarea.stage_id = etapa2
```

### Normalización de Proyectos

**Método:** `_normalizar_proyecto(proyecto, mapeo_dict, etapas_destino_ids, stats)`

**Lógica:**
```python
if not proyecto.type_ids:
    # Caso 1: Sin etapas → Asignar todas las destino
    nuevas_etapas = etapas_destino_ids
else:
    nuevas_etapas = set()
    for etapa in proyecto.type_ids:
        if etapa in etapas_destino:
            # Caso 2a: Coincide → Mantener
            nuevas_etapas.add(etapa)
        elif etapa in mapeo:
            # Caso 2b: Mapear → Sustituir
            nuevas_etapas.add(mapeo[etapa])
    
    # Caso 2c: Añadir faltantes
    nuevas_etapas.update(etapas_destino - nuevas_etapas)

proyecto.write({'type_ids': [(6, 0, nuevas_etapas)]})
```

### Normalización de Tareas

**Método:** `_normalizar_tareas(proyectos, mapeo_dict, stats)`

**Lógica:**
```python
tareas = env['project.task'].search([('project_id', 'in', proyectos.ids)])

for tarea in tareas:
    if tarea.stage_id in mapeo_dict:
        etapa_destino = mapeo_dict[tarea.stage_id]
        if tarea.stage_id != etapa_destino:
            tarea.write({'stage_id': etapa_destino.id})
            # El tracking de Odoo registra el cambio automáticamente
```

**Importante:** El cambio se registra en el chatter porque `stage_id` tiene `tracking=True` en la definición del modelo `project.task`.

---

## 💾 Sistema de Snapshots

### Estructura de Datos

**Formato JSON de estado_proyectos:**
```json
[
  {
    "id": 42,
    "name": "Proyecto Desarrollo Web",
    "type_ids": [1, 3, 5, 7, 9]
  },
  ...
]
```

**Formato JSON de estado_tareas:**
```json
[
  {
    "id": 156,
    "name": "Implementar API",
    "stage_id": 3
  },
  ...
]
```

### Rollback

**Método:** `snapshot.action_rollback()`

**Proceso:**
1. Valida que snapshot esté activo
2. Deserializa JSON de proyectos y tareas
3. Restaura `type_ids` de cada proyecto
4. Restaura `stage_id` de cada tarea
5. Desactiva snapshot (no puede reutilizarse)

**Importante:** El rollback NO deshace la creación de etapas destino si no existían.

---

## 🔍 Simulación

### Método: `_simular_normalizacion(proyectos)`

**Retorna:** Diccionario con estadísticas:
```python
{
    'proyectos_sin_etapas': [
        {'proyecto': 'Nombre', 'id': 42, 'etapas_a_añadir': 5}
    ],
    'proyectos_con_cambios': [
        {
            'proyecto': 'Nombre',
            'id': 42,
            'cambios': [
                {'tipo': 'sustituir', 'origen': 'Testing', 'destino': 'Realizada'},
                {'tipo': 'añadir', 'etapa': 'Pospuesta'}
            ]
        }
    ],
    'proyectos_sin_cambios': [...],
    'etapas_a_sustituir': [...],
    'etapas_a_añadir': [...],
    'tareas_a_actualizar': [
        {
            'tarea': 'Implementar API',
            'id': 156,
            'proyecto': 'Desarrollo Web',
            'etapa_actual': 'Testing',
            'etapa_nueva': 'Realizada'
        }
    ]
}
```

**Nota:** La simulación NO modifica la base de datos.

---

## 🗑️ Limpieza de Etapas Obsoletas

### Problema: Etapas Zombi

Después de normalizar, las etapas antiguas quedan en `project.task.type` sin estar en uso:

```python
# ANTES de normalizar:
TaskType.search([])  # 25 etapas

# DESPUÉS de normalizar:
proyectos[0].type_ids  # [Pendiente, En proceso, ...] (5 etapas)
tareas.mapped('stage_id')  # Solo usan las 5 etapas destino

TaskType.search([])  # ¡TODAVÍA 25 etapas! (20 sin uso)
```

### Comportamiento de Odoo

**Eliminación sin restricciones:**
```python
etapa = env['project.task.type'].browse(42)
etapa.unlink()  # Odoo PERMITE eliminarlo siempre

# Tareas con stage_id = 42
tarea.stage_id  # → False (NULL)
```

**NO hay `ondelete='restrict'` automático en Odoo base.**

### Solución Implementada

**Método:** `_limpiar_etapas_obsoletas()`

**Lógica:**
```python
for etapa in etapas_candidatas:
    # Verificación 1: ¿Está en algún proyecto?
    proyectos_count = Project.search_count([('type_ids', 'in', etapa.id)])
    if proyectos_count > 0:
        continue  # RETENER
    
    # Verificación 2: ¿La usa alguna tarea?
    tareas_count = Task.search_count([('stage_id', '=', etapa.id)])
    if tareas_count > 0:
        continue  # RETENER
    
    # Seguro eliminar
    etapa.unlink()
```

### Ejemplo de Logs

```
INFO: Analizando 20 etapas candidatas para eliminación
DEBUG: Etapa "Testing" RETENIDA: usada en 3 proyectos
DEBUG: Etapa "Blocked" RETENIDA: usada en 7 tareas
INFO: ✓ Etapa obsoleta eliminada: "Old Stage" (ID: 42)
INFO: ✓ Etapa obsoleta eliminada: "Deprecated" (ID: 51)
INFO: Limpieza completada: 15 etapas obsoletas eliminadas
INFO: Etapas retenidas (aún en uso): Testing (3 proyectos), Blocked (7 tareas)
```

### ⚠️ Consideraciones

1. **Opcional:** Usuario decide si activar limpieza
2. **Conservador:** Ante la duda, retiene la etapa
3. **Auditable:** Logs completos de cada decisión
4. **Rollback NO revierte eliminaciones:** El snapshot guarda `type_ids` y `stage_id`, 
   pero NO recrea etapas eliminadas del modelo `project.task.type`

---

## 🔒 Seguridad

### Permisos

```xml
<!-- security.xml -->
<record id="access_unificar_etapas_wizard_admin">
    <field name="group_id" ref="leulit_tarea.RT_proyectos_tareas_administrador"/>
    <field name="perm_read" eval="1"/>
    <field name="perm_create" eval="1"/>
    <field name="perm_write" eval="1"/>
    <field name="perm_unlink" eval="1"/>
</record>

<!-- Control de project.task.type -->
<record id="access_project_task_type_full_stages_admin">
    <field name="model_id" ref="project.model_project_task_type"/>
    <field name="group_id" ref="leulit_tarea.RT_proyectos_tareas_administrador"/>
    <field name="perm_read" eval="1"/>
    <field name="perm_create" eval="1"/>
    <field name="perm_write" eval="1"/>
    <field name="perm_unlink" eval="1"/>
</record>
```

**Acceso:** Solo grupo `RT_proyectos_tareas_administrador`

### Reglas de Registro (ir.rule)

Se implementan reglas adicionales para asegurar que SOLO el grupo específico puede modificar etapas:

```xml
<record id="project_task_type_rule_readonly">
    <field name="name">project.task.type: Solo lectura para usuarios normales</field>
    <field name="groups" eval="[(4, ref('base.group_user'))]"/>
    <field name="perm_read" eval="1"/>
    <field name="perm_create" eval="0"/>
    <field name="perm_write" eval="0"/>
    <field name="perm_unlink" eval="0"/>
</record>
```

**Efecto:** Incluso administradores generales NO pueden modificar etapas.

### Validaciones

1. **Constraint en wizard:**
```python
@api.constrains('aplicar_a_proyectos', 'proyecto_ids')
def _check_proyectos(self):
    if not self.aplicar_a_proyectos and not self.proyecto_ids:
        raise UserError(...)
```

2. **Validación de modo:**
```python
if self.modo_ejecucion == 'simulacion':
    raise UserError('Estás en modo SIMULACIÓN...')
```

3. **Confirmación adicional en vista:**
```xml
<button ... confirm="¿Estás seguro?..."/>
```

---

## 📊 Logging

### Niveles de Log

**INFO:**
- Inicio/fin de procesos
- Proyectos procesados
- Estadísticas finales

**DEBUG:**
- Detalles de cada cambio
- Tareas actualizadas individualmente

**Ejemplo:**
```python
_logger.info('Iniciando normalización para %s proyectos', len(proyectos))
_logger.info('Proyecto actualizado: "%s" (ID: %s)', proyecto.name, proyecto.id)
_logger.debug('Tarea "%s" actualizada: "%s" → "%s"', tarea.name, etapa_origen, etapa_destino)
```

### Ver Logs

```bash
docker logs -f helipistas_odoo | grep "normalización\|Snapshot\|Rollback"
```

---

## 🗂️ Estructura de Archivos

```
addons/leulit_tarea/
├── models/
│   ├── __init__.py
│   └── unificar_etapas_wizard.py     # 3 modelos + lógica + limpieza
├── views/
│   └── unificar_etapas_wizard.xml    # Vistas + acciones
├── security.xml                       # Permisos
├── menu.xml                          # Menús
├── NORMALIZACION_ETAPAS.md          # Guía usuario
└── NORMALIZACION_ETAPAS_TECNICA.md  # Este archivo
```

---

## 🔧 Configuración

### Etapas Destino

Definidas en la clase wizard:
```python
ETAPAS_DESTINO_TAREA = [
    'Pendiente',
    'En proceso',
    'Realizada',
    'Pospuesta',
    'N/A'
]
```

**Para modificar:** Editar esta constante y reiniciar módulo.

### Creación de Etapas Destino

**Método:** `_crear_etapas_destino()`

**Comportamiento:**
- Busca etapa por nombre exacto
- Si no existe, la crea con descripción predeterminada
- Se ejecuta automáticamente en Paso 1

---

## 🧪 Testing

### Caso de Prueba 1: Proyecto Sin Etapas

**Setup:**
```python
proyecto = env['project.project'].create({'name': 'Test'})
assert len(proyecto.type_ids) == 0
```

**Ejecución:** Normalizar

**Verificación:**
```python
assert len(proyecto.type_ids) == 5
assert 'Pendiente' in proyecto.type_ids.mapped('name')
```

### Caso de Prueba 2: Tarea Con Etapa Mapeada

**Setup:**
```python
etapa_testing = env['project.task.type'].create({'name': 'Testing'})
tarea = env['project.task'].create({
    'name': 'Test Task',
    'stage_id': etapa_testing.id
})
```

**Mapeo:** Testing → Realizada

**Verificación:**
```python
assert tarea.stage_id.name == 'Realizada'
```

### Caso de Prueba 3: Rollback

**Setup:** Ejecutar normalización con snapshot

**Verificación:**
```python
snapshot = env['leulit_tarea.unificar_etapas_snapshot'].search([], limit=1)
assert snapshot.activo == True
snapshot.action_rollback()
assert snapshot.activo == False
assert proyecto.type_ids == estado_original
```

### Caso de Prueba 4: Limpieza de Etapas Obsoletas [NUEVO]

**Setup:**
```python
# Crear etapa obsoleta sin uso
etapa_obsoleta = env['project.task.type'].create({'name': 'Obsoleta'})
initial_count = env['project.task.type'].search_count([])

# Ejecutar normalización con limpieza
wizard.limpiar_etapas_obsoletas = True
wizard.action_unificar_etapas()
```

**Verificación:**
```python
final_count = env['project.task.type'].search_count([])
assert final_count < initial_count
assert wizard.etapas_eliminadas > 0
# Etapa obsoleta fue eliminada
assert not env['project.task.type'].search([('name', '=', 'Obsoleta')])
```

**Caso negativo:**
```python
# Etapa en uso NO se elimina
tarea.write({'stage_id': etapa_en_uso.id})
wizard.action_unificar_etapas()
assert env['project.task.type'].search([('id', '=', etapa_en_uso.id)])
```

---

## 🚨 Troubleshooting

### Error: "No se encontraron etapas destino"

**Causa:** Las etapas no existen y no se pudieron crear

**Solución:**
1. Crear manualmente: `project.task.type`
2. Verificar permisos de creación

### Error: "Este snapshot ya no está activo"

**Causa:** Intentar hacer rollback de un snapshot ya usado

**Solución:** No hay. Necesitas un nuevo snapshot o backup de BD.

### Tareas No Se Actualizan

**Causa:** La etapa de la tarea no está en el mapeo

**Solución:** Verificar que todas las etapas existentes estén mapeadas en Paso 2

### Performance Lento con Muchos Proyectos

**Causa:** Procesamiento secuencial de miles de tareas

**Solución:** 
- Aplicar por lotes de proyectos
- Ejecutar fuera de horario laboral
- Considerar optimización con SQL para casos masivos

---

## 📈 Performance

### Complejidad

- **Análisis:** O(P × E) donde P = proyectos, E = etapas por proyecto
- **Normalización:** O(P + T) donde T = total de tareas
- **Rollback:** O(P + T)

### Estimaciones

| Escenario | Tiempo Estimado |
|-----------|-----------------|
| 10 proyectos, 100 tareas | ~2 segundos |
| 100 proyectos, 1,000 tareas | ~10 segundos |
| 1,000 proyectos, 10,000 tareas | ~2 minutos |

**Nota:** Depende de hardware y carga del servidor.

---

## 🔄 Ciclo de Vida

### Wizard (TransientModel)

- **Duración:** ~1 hora en memoria
- **Limpieza:** Automática por cron de Odoo
- **Persistencia:** Solo snapshot se mantiene

### Snapshot (Model)

- **Duración:** Indefinida
- **Limpieza:** Manual (no hay auto-limpieza)
- **Desactivación:** Automática al usar rollback

---

## 📚 Referencias

### Modelos Odoo Base

- `project.project` - Proyectos
- `project.task` - Tareas
- `project.task.type` - Etapas/Stages

### Documentación Odoo

- [TransientModel](https://www.odoo.com/documentation/17.0/developer/reference/backend/orm.html#transient-models)
- [One2many/Many2many](https://www.odoo.com/documentation/17.0/developer/reference/backend/orm.html#relational-fields)
- [Actions](https://www.odoo.com/documentation/17.0/developer/reference/backend/actions.html)

---

## 🐛 Debugging

### Activar Modo Debug

```python
# En el wizard, añadir temporalmente:
import pdb; pdb.set_trace()
```

### Inspeccionar Estado

```python
# En shell de Odoo:
wizard = env['leulit_tarea.unificar_etapas_wizard'].browse(ID)
wizard.mapeo_linea_ids
wizard.simulacion_resultado
```

### Ver Cambios en Tiempo Real

```python
# Activar logging en DEBUG:
_logger.setLevel(logging.DEBUG)
```

---

## 🎓 Mantenimiento

### Añadir Nueva Etapa Destino

1. Editar `ETAPAS_DESTINO_TAREA`
2. Actualizar módulo
3. Ejecutar wizard (creará la nueva etapa)

### Modificar Lógica de Mapeo

1. Editar `_normalizar_proyecto()` o `_normalizar_tareas()`
2. Actualizar tests
3. Actualizar documentación

### Añadir Filtros en Paso 1

1. Añadir campo al wizard
2. Modificar dominio en `action_analizar_etapas()`
3. Añadir campo a vista XML

---

*Última actualización: Enero 2026*
*Versión: 17.0.1.0.0*
*Desarrollador: Sistema Helipistas*
