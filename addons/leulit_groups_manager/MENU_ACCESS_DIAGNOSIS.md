# Guía de Diagnóstico de Acceso a Menús

## ¿Qué hace esta funcionalidad?

La herramienta de diagnóstico de acceso a menús te permite:
1. Ver por qué un usuario **puede** o **no puede** ver un menú específico
2. Identificar exactamente qué grupos hacen falta para dar acceso
3. Entender la jerarquía de menús padre y cuál está bloqueando el acceso

## Conceptos Clave

### 1. User's Direct Groups (Grupos Directos del Usuario)
Son los grupos **explícitamente asignados** al usuario. Los ves cuando:
- Editas un usuario → pestaña "Grupos de Acceso"
- Marcas/desmarcas checkboxes

**Ejemplo**: Si asignas "Responsable de Operaciones" a un usuario, ese es un grupo directo.

### 2. Implied Groups (Grupos Implicados/Heredados)
Son grupos que el usuario obtiene **automáticamente** por tener otros grupos.

**¿Cómo funciona?**
- En Odoo, un grupo puede tener `implied_ids` (grupos que implica)
- Si el grupo A implica al grupo B, al asignar A al usuario, automáticamente obtiene B
- Estos grupos NO aparecen marcados en el formulario del usuario, pero el usuario los tiene

**Ejemplo Real (del proyecto Helipistas)**:
```
ROperaciones_responsable 
  → implica ROperaciones_piloto
    → implica ROperaciones_operador
      → implica ROperaciones_alumno
        → implica ROperaciones_piloto_externo
          → implica RBase_hide
            → implica RBase_employee
              → implica RBase
```

Si asignas `ROperaciones_responsable` a un usuario:
- **Grupo Directo**: `ROperaciones_responsable` (1 grupo)
- **Grupos Implicados**: Los otros 7 grupos (automáticos)

### 3. Menús Padre - El Problema Crítico

**Regla de Oro en Odoo**: Para ver un menú, el usuario debe tener acceso a **TODA la jerarquía de menús padre**.

**Ejemplo del problema reportado**: `Projecto/Proyectos`
```
Projecto (menú padre - nivel 1)
  └── Proyectos (menú hijo - nivel 2)
```

Si un usuario tiene acceso a "Proyectos" pero NO a "Projecto":
- ✅ El usuario técnicamente puede acceder a "Proyectos"
- ❌ **NO verá "Proyectos" en la UI** porque el menú padre está bloqueado
- ⚠️ El sistema antes solo decía "PROBLEM FOUND" pero no indicaba qué hacer

**Ahora la herramienta muestra**:
1. Una tabla con cada menú padre
2. Qué grupos requiere cada uno
3. Si el usuario tiene acceso o no
4. **SOLUCIÓN**: Exactamente qué grupo(s) añadir para desbloquear cada menú padre

## Cómo Usar el Diagnóstico

### Opción 1: Desde la Ficha del Usuario

1. Ir a **Configuración > Usuarios y Compañías > Usuarios**
2. Abrir el usuario afectado
3. Click en **"Diagnosticar Menú"** (botón en la parte superior)
4. Seleccionar el menú que no se ve
5. Ver el diagnóstico completo

### Opción 2: Desde el Menú Principal

1. Ir a **Ajustes > Grupos > Diagnosticar Acceso a Menús**
2. Seleccionar usuario
3. Seleccionar menú
4. Ver diagnóstico

## Interpretando el Diagnóstico

### Sección 1: Jerarquía de Menús con Colores
```
CRM / Configuración / Equipos de Ventas
🟢 Verde = Usuario tiene acceso
🔴 Rojo = Usuario NO tiene acceso
```

### Sección 2: Detalles del Menú
- Nombre completo, ID, XML ID
- Grupos requeridos por el menú

### Sección 3: Grupos del Usuario
- **Direct Groups**: Los que asignaste manualmente
- **Implied Groups**: Los que obtuvo automáticamente (con indicación de qué grupo directo lo implica)

### Sección 4: Análisis de Acceso
- ✅ "USER HAS ACCESS": El usuario puede acceder al menú
- ❌ "USER DOES NOT HAVE ACCESS": Falta algún grupo requerido

### Sección 5: Menús Padre (LA MÁS IMPORTANTE)

**Nueva funcionalidad**: Tabla detallada con:

| Menu | Access | Required Groups | Status |
|------|--------|----------------|--------|
| Projecto | ✗ | • Grupo A<br>• Grupo B | ✗ User is missing ALL required groups |
| Proyectos | ✓ | • Grupo C | ✓ User has: Grupo C |

**Nueva sección de solución**: 
Si hay menús padre bloqueados, muestra:
```
🛠️ Solution: Add the following groups to the user

1. Projecto (Path: Projecto)
   Choose ONE of these groups:
   • Administration / Settings (link)
   • Project / Manager (link)
```

## Ejemplo Real: Caso CRM/Ventas

### Problema Reportado Anteriormente
Usuario con grupo "Solo mostrar documentos propios" no veía CRM/Ventas.

### Diagnóstico Revelaba
- Usuario tenía `sale.group_sale_salesman` ✅
- Pero faltaba `sales_team.group_sale_salesman` para acceso base a CRM ❌

### Solución
Añadir **ambos grupos**:
1. `sale.group_sale_salesman` (filtrado de documentos)
2. `sales_team.group_sale_salesman` (acceso base a CRM)

## Mejoras Implementadas

### Antes
- ✅ Detectaba problema de menús padre
- ❌ Solo mostraba "PROBLEM FOUND" sin detalles
- ❌ No indicaba qué grupos faltaban

### Ahora
- ✅ Detecta problema de menús padre
- ✅ Muestra tabla detallada de cada menú padre
- ✅ Indica qué grupos requiere cada menú padre
- ✅ Muestra el estado de acceso del usuario para cada menú padre
- ✅ **Proporciona solución específica**: Lista exactamente qué grupos añadir
- ✅ Explica qué son los grupos directos vs implicados
- ✅ Muestra qué grupo directo implica a cada grupo implicado

## Tips

1. **Grupos Implicados son Automáticos**: No necesitas asignarlos manualmente
2. **Jerarquía de Menús es Crítica**: Siempre verifica menús padre
3. **Un Grupo es Suficiente**: Si un menú requiere A o B, con uno basta
4. **Enlaces Clicables**: Los grupos en la solución son clicables para ir directo a editar el grupo

---

## Problema Reportado Original (Resuelto)

### Causa Probable
En Odoo, un menú es visible si:
1. Usuario tiene ≥1 de los grupos requeridos por el menú
2. Usuario tiene acceso a TODOS los menús padre
3. Usuario tiene grupos base de la aplicación

### Grupo "Solo mostrar documentos propios"
- Es `sale.group_sale_salesman`
- **NO da acceso base a Ventas**
- Solo añade reglas de filtrado
- Requiere otro grupo para acceso base

### Solución
El usuario necesita **DOS grupos**:
1. **Usuario: Solo mostrar documentos propios** (`sale.group_sale_salesman`) - reglas filtrado
2. **Usuario: Todos los documentos** (`sales_team.group_sale_salesman`) - acceso base CRM

O:
1. **Usuario: Solo mostrar documentos propios** + **Administrador** (`sales_team.group_sale_manager`)
   - ❌ Grupos que le faltan
   - 🔗 Jerarquía de menús padre
   - 💡 Solución sugerida

### Opción 2: Verificar Grupos Necesarios

```python
# Para ver qué grupos requiere un menú:
menu = self.env.ref('sale.sale_menu_root')  # Menú principal Ventas
print("Grupos requeridos:", menu.groups_id.mapped('full_name'))

# Para ver grupos de un usuario:
user = self.env['res.users'].browse(USER_ID)
print("Grupos del usuario:", user.groups_id.mapped('full_name'))
```

## Verificación Manual

### Paso 1: Verificar Grupos del Menú
```sql
SELECT g.name, g.full_name
FROM ir_ui_menu_group_rel mgr
JOIN res_groups g ON g.id = mgr.gid
WHERE mgr.menu_id = (SELECT id FROM ir_ui_menu WHERE name = 'Ventas' LIMIT 1);
```

### Paso 2: Verificar Grupos del Usuario
```sql
SELECT g.name, g.full_name
FROM res_groups_users_rel gur
JOIN res_groups g ON g.id = gur.gid
WHERE gur.uid = USER_ID;
```

### Paso 3: Verificar Intersección
Los grupos del usuario deben incluir AL MENOS UNO de los grupos del menú.

## Solución Rápida

### Mediante UI:
1. Ir al usuario
2. Pestaña **"Permisos de Acceso"**
3. En **Ventas** seleccionar: **"Usuario: Todos los documentos"**
4. Mantener también: **"Usuario: Solo mostrar documentos propios"**

### Mediante Código:
```python
user = self.env['res.users'].browse(USER_ID)
group_all_docs = self.env.ref('sales_team.group_sale_salesman')
user.groups_id = [(4, group_all_docs.id)]
```

## Nuevas Funcionalidades Añadidas

### 1. Ver Menús Accesibles
Botón que muestra todos los menús que el usuario puede ver, organizados por jerarquía.

### 2. Diagnosticar Acceso a Menú
Wizard que explica en detalle:
- ¿Por qué el usuario no ve un menú específico?
- ¿Qué grupos le faltan?
- ¿Hay problemas en la jerarquía de menús padre?
- Solución paso a paso

### 3. Análisis Completo
- Grupos directos vs grupos implícitos (heredados)
- Visualización de la cadena de menús padre
- Identificación de "cuellos de botella" en permisos

## Recomendaciones

1. **Siempre verificar grupos base**: Los grupos de "Solo mostrar documentos propios" son complementarios, no principales
2. **Usar el diagnóstico**: Antes de añadir grupos aleatoriamente, usar la herramienta de diagnóstico
3. **Documentar configuraciones**: Mantener registro de qué grupos necesita cada rol
4. **Revisar jerarquía**: A veces el problema está en un menú padre, no en el menú final
