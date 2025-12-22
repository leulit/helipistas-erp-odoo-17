# Solución al Problema de Acceso a Menús CRM/Ventas

## Problema Reportado
Usuario con grupo "Solo mostrar documentos propios" no puede ver los menús CRM y VENTAS, aunque el grupo tiene esos menús asignados.

## Diagnóstico

### Causa Probable
En Odoo, un menú es visible para un usuario si cumple TODAS estas condiciones:

1. **El usuario tiene al menos uno de los grupos requeridos por el menú**
2. **El usuario tiene acceso a TODOS los menús padre** (jerarquía completa)
3. **El usuario tiene los grupos base de la aplicación**

### Grupo "Solo mostrar documentos propios"
Este es el grupo `sale.group_sale_salesman` que:
- **NO da acceso a la aplicación base de Ventas**
- Solo añade reglas de registro (record rules) para filtrar documentos
- Requiere que el usuario tenga OTRO grupo que dé acceso a Ventas

### Solución

El usuario necesita **DOS grupos**:

1. **Usuario: Solo mostrar documentos propios** (`sale.group_sale_salesman`)
   - Para las reglas de filtrado

2. **Usuario: Todos los documentos** (`sales_team.group_sale_salesman`) 
   - Para el acceso base a Ventas/CRM

O alternativamente:

1. **Usuario: Solo mostrar documentos propios** (`sale.group_sale_salesman`)
2. **Administrador** (`sales_team.group_sale_manager`)

## Cómo Usar el Nuevo Diagnóstico

### Opción 1: Desde la Ficha del Usuario

1. Ir a **Configuración > Usuarios y Compañías > Usuarios**
2. Abrir el usuario afectado
3. En la parte superior verás 3 nuevos botones:
   - **Grupos**: Ver todos los grupos asignados
   - **Menús**: Ver todos los menús accesibles
   - **Diagnosticar Menú**: Analizar por qué no ve un menú específico

4. Hacer clic en **"Diagnosticar Menú"**
5. Seleccionar el menú "CRM" o "Ventas"
6. El sistema mostrará:
   - ✅ Grupos que tiene el usuario
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
