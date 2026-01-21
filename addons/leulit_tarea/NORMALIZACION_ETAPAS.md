# Normalización de Etapas - Guía de Usuario

## 📌 ¿Qué hace esta herramienta?

Esta herramienta permite **estandarizar las etapas** en todos los proyectos y tareas del sistema, asegurando que todos usen el mismo conjunto de etapas normalizadas.

## 🎯 Conceptos Importantes

### Etapas de Proyecto vs Etapas de Tareas

Es importante entender la diferencia:

| Concepto | Descripción | Campo Técnico | Ejemplo |
|----------|-------------|---------------|---------|
| **Etapas del Proyecto** | Etapas DISPONIBLES para usar en ese proyecto | `project.project.type_ids` | [Pendiente, En proceso, Realizada, Pospuesta, N/A] |
| **Etapa de una Tarea** | Etapa ACTUAL en la que está la tarea | `project.task.stage_id` | Tarea X está en "En proceso" |

**Esta herramienta modifica AMBAS:**
1. ✅ Normaliza las etapas **disponibles** en cada proyecto
2. ✅ Actualiza la etapa **actual** de cada tarea según el mapeo definido

### Etapas Destino Normalizadas

Las etapas estándar que se aplicarán son:
- **Pendiente**
- **En proceso**
- **Realizada**
- **Pospuesta**
- **N/A**

---

## 🚀 Cómo Usar la Herramienta

### Acceso

**Menú:** `Gestión tareas → Configuración → Normalizar Etapas`

**Permisos:** Solo administradores de etapas (`RT_proyectos_tareas_administrador`)

⚠️ **Importante:** Este grupo tiene control exclusivo sobre las etapas de proyectos y tareas.

---

## 📋 Proceso Paso a Paso

### **PASO 1: Selección de Proyectos**

**¿Qué hacer?**
Decide qué proyectos quieres normalizar:

- ☑️ **Aplicar a Todos los Proyectos**: Normaliza TODOS los proyectos del sistema
- 📋 **Proyectos Específicos**: Marca solo los proyectos que quieres normalizar

**Resultado:** Click en "Siguiente: Mapear Etapas" →

---

### **PASO 2: Mapeo de Etapas**

**¿Qué verás?**
Una tabla con todas las etapas existentes encontradas:

| Etapa Actual | → Etapa Destino | Proyectos | Tareas |
|--------------|-----------------|-----------|---------|
| To Do | Pendiente | 12 | 89 |
| Doing | En proceso | 15 | 156 |
| Testing | Realizada | 8 | 34 |
| Blocked | Pospuesta | 10 | 23 |

**¿Qué hacer?**
- Revisa el mapeo automático (el sistema pre-selecciona coincidencias)
- Modifica el mapeo si no estás de acuerdo
- Las columnas "Proyectos" y "Tareas" te muestran cuántos se afectarán

**Resultado:** Click en "Simular Cambios" →

---

### **PASO 3: Simulación y Ejecución**

#### A) Simulación (Vista Previa)

**¿Qué verás?**
Un reporte detallado mostrando EXACTAMENTE qué se va a cambiar:

```
═══════════════════════════════════════════════════════
REPORTE DE SIMULACIÓN - CAMBIOS A REALIZAR
═══════════════════════════════════════════════════════

📝 PROYECTOS SIN ETAPAS (3)
───────────────────────────────────────────────────────
  • Proyecto Alpha → Se añadirán 5 etapas
  • Proyecto Beta → Se añadirán 5 etapas

🔄 PROYECTOS CON CAMBIOS (12)
───────────────────────────────────────────────────────
  • Desarrollo Web:
    - Sustituir 'Testing' → 'Realizada'
    - Añadir etapa 'Pospuesta'
  • App Mobile:
    - Sustituir 'Blocked' → 'Pospuesta'

📋 TAREAS A ACTUALIZAR (156)
───────────────────────────────────────────────────────
  • [Desarrollo Web] Implementar API
    'Testing' → 'Realizada'
  • [Desarrollo Web] Diseño UI
    'Blocked' → 'Pospuesta'
```

**Estadísticas:**
```
Proyectos sin etapas: 3
Proyectos con cambios: 12
Proyectos sin cambios: 5
Etapas a sustituir: 27
Etapas a añadir: 42
Tareas a actualizar: 156
```

#### B) Ejecución Real

**¿Qué hacer?**
1. Revisa el reporte de simulación
2. Si estás de acuerdo:
   - Cambia el modo a: **🔴 Ejecución Real**
   - Marca: **☑️ Crear Snapshot para Rollback** (RECOMENDADO)
   - Opcionalmente marca: **☑️ Eliminar Etapas Obsoletas** (elimina etapas antiguas sin uso)
   - Click en: **🚀 EJECUTAR NORMALIZACIÓN**
   - Confirma: "¿Estás seguro?"

**Resultado:** Los cambios se aplican →

---

## �️ Limpieza de Etapas Obsoletas (OPCIONAL)

### ¿Qué hace?

Después de normalizar, las etapas antiguas (ej. "Testing", "Blocked", "To Do") pueden quedar en la base de datos **sin estar en uso**.

La opción **"Eliminar Etapas Obsoletas"** limpia automáticamente estas etapas huérfanas.

### ¿Cuándo se elimina una etapa?

**SOLO** cuando cumple **TODAS** estas condiciones:

| Condición | Explicación |
|-----------|-------------|
| ❌ NO es etapa destino | No es Pendiente, En proceso, Realizada, Pospuesta o N/A |
| ❌ NO está en proyectos | Ningún proyecto la tiene en `type_ids` (etapas disponibles) |
| ❌ NO está en tareas | Ninguna tarea la tiene como `stage_id` (etapa actual) |

### ⚠️ Comportamiento de Odoo sin esta opción

Si NO activas la limpieza:
- ✅ La normalización funciona perfectamente
- ⚠️ Las etapas antiguas quedan en la base de datos (sin uso)
- ⚠️ Con el tiempo puedes acumular 50+ etapas "zombi"
- ℹ️ Puedes eliminarlas manualmente desde `Configuración → Tipos de Tareas`

### 🛡️ Seguridad

```python
# Ejemplo de verificación antes de eliminar:
if proyecto_con_etapa.count() == 0 and tarea_con_etapa.count() == 0:
    etapa.unlink()  # Seguro eliminar
else:
    # RETENER - aún en uso
```

**El sistema registra en logs:**
- ✓ Etapas eliminadas (nombre e ID)
- ℹ️ Etapas retenidas (razón: en X proyectos o Y tareas)

---

## �🔙 Sistema de Rollback (Deshacer Cambios)

### ¿Algo salió mal?

**No hay problema. Puedes revertir TODOS los cambios:**

### Cómo Hacer Rollback

1. **Ve a:** `Gestión tareas → Configuración → Snapshots de Rollback`

2. **Selecciona** el snapshot más reciente (el que se creó antes de la normalización)

3. **Click en:** `🔙 Restaurar Estado Anterior`

4. **Confirma** la acción

5. ✅ **TODO vuelve a como estaba antes:**
   - Proyectos con sus etapas originales
   - Tareas con sus etapas originales
   - Historial completo restaurado

### ⚠️ Importante sobre Snapshots

- El snapshot se crea AUTOMÁTICAMENTE antes de aplicar cambios (si está marcada la opción)
- Solo puede usarse UNA VEZ
- Después de usarlo, se marca como "Inactivo"
- Guarda información de TODOS los proyectos y tareas afectados

---

## 📊 ¿Qué Sucede Exactamente?

### Para Proyectos

La herramienta actualiza las **etapas disponibles** del proyecto (`type_ids`):

| Situación | Acción | Ejemplo |
|-----------|--------|---------|
| **Proyecto sin etapas** | Asigna todas las etapas destino | Proyecto vacío → [Pendiente, En proceso, Realizada, Pospuesta, N/A] |
| **Etapa coincide** | No hace nada (ya correcta) | Proyecto tiene "En proceso" → Se mantiene |
| **Etapa mapeada** | Sustituye según mapeo | Proyecto tiene "Testing" → Cambia a "Realizada" |
| **Etapa faltante** | Añade la etapa destino | Proyecto no tiene "Pospuesta" → Se añade |

### Para Tareas

La herramienta actualiza la **etapa actual** de cada tarea (`stage_id`):

| Situación | Acción | Ejemplo |
|-----------|--------|---------|
| **Tarea con etapa mapeada** | Cambia a etapa destino | Tarea en "Testing" → Cambia a "Realizada" |
| **Tarea con etapa correcta** | No hace nada | Tarea en "En proceso" → Se mantiene |
| **Cambio registrado** | Se guarda en historial | El chatter muestra: "Etapa cambiada de Testing a Realizada" |

---

## ✅ Resultado Final

Después de ejecutar la normalización:

### Todos los proyectos seleccionados tendrán:
- ✅ Las mismas 5 etapas disponibles
- ✅ Etapas estandarizadas y homogéneas
- ✅ Todas las etapas destino configuradas

### Todas las tareas de esos proyectos tendrán:
- ✅ Su etapa actualizada según el mapeo
- ✅ Historial del cambio en el chatter
- ✅ Etapa válida dentro de las disponibles del proyecto

### Base de datos limpia (si activaste limpieza):
- ✅ Solo existen las 5 etapas destino + etapas en uso
- ✅ Etapas obsoletas eliminadas
- ✅ Logs detallados de lo eliminado

---

## 🛡️ Seguridad y Validaciones

### Protecciones Implementadas

1. **Modo Simulación Obligatorio:**
   - No puedes ejecutar sin antes simular
   - Ves exactamente qué se va a cambiar

2. **Confirmación Doble:**
   - Debes cambiar a modo "Ejecución Real"
   - Debes confirmar en popup adicional

3. **Snapshot Automático:**
   - Se guarda el estado antes de cambiar
   - Puedes hacer rollback completo

4. **Permisos:**
   - Solo grupo `RT_proyectos_tareas_administrador` puede acceder
   - Este grupo tiene control exclusivo sobre etapas
   - Otros usuarios (incluso administradores) NO pueden modificar etapas
   - Acción registrada con usuario y fecha

5. **Logging Completo:**
   - Cada cambio se registra en logs del sistema
   - Auditoría completa de la operación

---

## 📝 Casos de Uso Comunes

### Caso 1: Estandarizar Proyectos Nuevos y Antiguos

**Problema:** Tenemos 50 proyectos con etapas diferentes
**Solución:** Aplicar normalización a todos
**Resultado:** Todos usan [Pendiente, En proceso, Realizada, Pospuesta, N/A]

### Caso 2: Migración de Nomenclatura

**Problema:** Usábamos "To Do", "Doing", "Done"
**Solución:** Mapear: To Do→Pendiente, Doing→En proceso, Done→Realizada
**Resultado:** Todas las tareas se actualizan con la nueva nomenclatura

### Caso 3: Limpieza de Etapas Obsoletas

**Problema:** Proyectos con 20 etapas diferentes, muchas sin usar
**Solución:** Normalizar a las 5 etapas estándar
**Resultado:** Proyectos limpios y organizados

---

## ❓ Preguntas Frecuentes

### ¿Puedo deshacer los cambios?
**Sí**, si creaste un snapshot (recomendado), puedes hacer rollback completo.

### ¿Se pierde información?
**No**, el historial de cambios se mantiene en el chatter de cada tarea.

### ¿Puedo aplicar solo a algunos proyectos?
**Sí**, desmarca "Aplicar a Todos" y selecciona los proyectos específicos.

### ¿Qué pasa si una tarea tiene una etapa que no se mapea?
**Se mantiene sin cambios** hasta que la mapees manualmente.

### ¿Se pueden añadir más etapas destino?
**Sí**, pero requiere modificación del código en `ETAPAS_DESTINO_TAREA`.

### ¿Afecta a proyectos archivados?
**No**, solo proyectos activos.

### ¿Puedo simular varias veces antes de ejecutar?
**Sí**, puedes simular cuantas veces quieras sin aplicar cambios.

### ¿Debo activar "Eliminar Etapas Obsoletas"?
**Recomendación:** Sí, si quieres mantener la base de datos limpia.
- ✅ Seguro: Solo elimina etapas completamente sin uso
- ✅ Logs detallados de qué se elimina y qué se retiene
- ⚠️ Si tienes dudas, déjalo desmarcado y elimina manualmente después

### ¿Qué pasa si elimino una etapa en uso por error?
**No puede pasar:** El sistema verifica que NO esté en uso antes de eliminar.
Si una etapa está asignada a algún proyecto o tarea, se RETIENE automáticamente.

---

## 🆘 Soporte

Si tienes problemas o dudas:

1. **Revisa los logs:** `docker logs -f helipistas_odoo`
2. **Verifica permisos:** Asegúrate de pertenecer al grupo `RT_proyectos_tareas_administrador`
3. **Consulta snapshots:** Verifica que se creó el snapshot
4. **Contacta a:** Equipo de IT/Desarrollo

### ⚠️ Restricciones de Seguridad

**Solo el grupo `RT_proyectos_tareas_administrador` puede:**
- ✅ Crear nuevas etapas
- ✅ Modificar etapas existentes
- ✅ Eliminar etapas
- ✅ Ejecutar la normalización de etapas

**Otros usuarios (incluso administradores generales):**
- ✅ Pueden VER las etapas
- ✅ Pueden USAR las etapas en sus tareas
- ❌ NO pueden crear/modificar/eliminar etapas
- ❌ NO pueden acceder a la herramienta de normalización

---

## 📌 Resumen Ejecutivo

**En una frase:** Esta herramienta estandariza las etapas de proyectos y tareas en todo el sistema, con mapeo personalizado, simulación previa y capacidad de rollback.

**Tiempo estimado:** 5-10 minutos (dependiendo del número de proyectos)

**Riesgo:** Mínimo (con snapshot y simulación previa)

**Beneficio:** Homogeneización completa de etapas en todo el sistema

---

*Última actualización: Enero 2026*
*Versión: 17.0.1.0.0*
*Módulo: leulit_tarea*
