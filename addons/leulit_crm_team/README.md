# Leulit CRM Team Security

## Descripción
Módulo que añade un grupo de seguridad intermedio para CRM y Ventas, permitiendo a los usuarios ver sus propios registros y los de sus equipos de ventas.

## Problema que Resuelve

**Situación:** Un usuario añadido al equipo "Taxi" puede ver oportunidades tanto de "Taxi" como de "Ventas" (incluso sin estar en "Ventas").

**Causa:** El grupo estándar de Odoo "Usuario: Todos los documentos" (`sales_team.group_sale_salesman`) permite ver TODO sin restricción de equipos.

**Solución:** Nuevo grupo intermedio que filtra por equipos de ventas del usuario.

---

## Grupos de Seguridad

### 1. Usuario: Solo mostrar documentos propios (`sale.group_sale_salesman`)
- **Ve:** Solo sus propios registros (donde `user_id = yo`)
- **Uso:** Para comerciales que trabajan individualmente sin visibilidad de equipo

### 2. Usuario: Ver documentos de mis equipos (**NUEVO** - `leulit_crm_team.group_sale_salesman_team`)
- **Ve:** Sus registros + registros de sus equipos de ventas
- **Uso:** Para comerciales que colaboran en equipos (caso más común)
- **Hereda de:** "Solo mostrar documentos propios"
- **Regla:** `user_id = yo OR user_id = False OR team_id IN mis_equipos`

### 3. Usuario: Todos los documentos (`sales_team.group_sale_salesman`)
- **Ve:** TODO sin restricción de equipos ni usuarios
- **Uso:** Para gerentes de ventas o roles de supervisión

### 4. Administrador (`sales_team.group_sale_manager`)
- **Ve:** TODO + gestión completa
- **Uso:** Director comercial

---

## Instalación

1. **El módulo ya está en** `addons/leulit_crm_team/`
2. **Reiniciar Odoo:**
   ```bash
   docker restart helipistas_odoo_17
   ```
3. **Actualizar lista de módulos:**
   - Ir a **Apps** en Odoo
   - Menú superior derecho → **Actualizar lista de aplicaciones**
4. **Instalar módulo:**
   - Buscar "Leulit CRM Team Security"
   - Click en **Instalar**

---

## Configuración de Usuarios

### Paso 1: Editar usuario
1. Ir a **Configuración > Usuarios y Compañías > Usuarios**
2. Seleccionar el usuario (ej: el que estaba viendo oportunidades de otros equipos)

### Paso 2: Configurar grupos de ventas
En la pestaña **Ventas**, sección **Acceso**:

- ✅ **Activar:** "Usuario: Ver documentos de mis equipos" (nuevo grupo)
- ❌ **Desactivar:** "Usuario: Todos los documentos" (si estaba activo)

### Paso 3: Asignar equipos de ventas
En la pestaña **Ventas**, sección **Equipos de ventas**:

- ✅ Añadir solo los equipos a los que debe tener acceso (ej: "Taxi")
- ❌ NO añadir "Ventas" si no debe verlo

### Paso 4: Guardar
Click en **Guardar**

---

## Resultado Esperado

| Usuario | Equipos asignados | Grupo activo | Ve oportunidades de... |
|---------|-------------------|--------------|------------------------|
| Juan | Taxi | Ver mis equipos | Equipo "Taxi" + propias + sin asignar |
| María | Taxi, Ventas | Ver mis equipos | Equipos "Taxi" + "Ventas" + propias + sin asignar |
| Pedro | (ninguno) | Todos los documentos | TODAS las oportunidades de todos los equipos |
| Ana | (ninguno) | Administrador | TODO + gestión completa |

---

## Modelos Afectados

Este módulo aplica reglas de seguridad a:

- ✅ **crm.lead** (Leads y Oportunidades)
- ✅ **sale.order** (Presupuestos y Pedidos de Venta)

Ambos modelos tienen el campo `team_id` que se usa para filtrar por equipo.

---

## Reglas de Dominio Implementadas

### Para CRM Leads:
```python
[
    '|',
        ('user_id', '=', user.id),              # Asignado a mí
    '|',
        ('user_id', '=', False),                # Sin asignar (nadie)
        ('team_id', 'in', user.sale_team_ids.ids)  # En alguno de mis equipos
]
```

### Para Sale Orders:
```python
[
    '|',
        ('user_id', '=', user.id),              # Asignado a mí
    '|',
        ('user_id', '=', False),                # Sin asignar (nadie)
        ('team_id', 'in', user.sale_team_ids.ids)  # En alguno de mis equipos
]
```

**Lógica:** El usuario verá un registro si cumple CUALQUIERA de las 3 condiciones (OR lógico).

---

## Pruebas Recomendadas

1. **Crear usuario de prueba** con acceso al equipo "Taxi" únicamente
2. **Crear oportunidades:**
   - Una asignada al equipo "Taxi" → ✅ Debe verla
   - Una asignada al equipo "Ventas" → ❌ NO debe verla
   - Una sin equipo asignado → ✅ Debe verla
   - Una asignada a él mismo (sin equipo) → ✅ Debe verla
3. **Verificar visibilidad** en el listado de oportunidades

---

## Ventajas

1. ✅ **No modifica grupos estándar** de Odoo (compatible con actualizaciones)
2. ✅ **Herencia limpia** de permisos existentes (principio Open/Closed)
3. ✅ **Flexible:** Usuarios pueden estar en múltiples equipos
4. ✅ **Escalable:** Fácil extender a otros modelos (ej: `crm.claim`, `project.task`)
5. ✅ **Auditable:** Cada usuario solo ve lo que debe ver
6. ✅ **Mantenible:** Documentación clara y reglas explícitas

---

## Solución de Problemas

### Problema: Usuario sigue viendo todo
- **Verificar** que NO tenga activo "Usuario: Todos los documentos"
- **Verificar** que SÍ tenga activo "Usuario: Ver documentos de mis equipos"
- **Verificar** que solo esté en los equipos correctos

### Problema: Usuario no ve nada
- **Verificar** que tenga al menos un equipo asignado en su perfil
- **Verificar** que el grupo "Usuario: Ver documentos de mis equipos" esté instalado
- **Revisar logs** de Odoo para errores de reglas de seguridad

### Problema: El módulo no aparece
- **Actualizar lista de aplicaciones** desde el menú Apps
- **Verificar** que el módulo esté en `addons/leulit_crm_team/`
- **Reiniciar** Odoo si acabas de añadir el módulo

---

## Extensión Futura

Si necesitas aplicar la misma lógica a otros modelos:

1. Añadir nuevos `<record>` en `security/crm_security_rules.xml`
2. Cambiar `model_id` al modelo deseado
3. Asegurarse que el modelo tenga campo `team_id` y `user_id`
4. Actualizar el módulo: `-u leulit_crm_team`

---

## Soporte

Para cualquier duda o problema, contactar con el equipo de desarrollo de Leulit.

**Versión:** 17.0.1.0.0  
**Última actualización:** 22 Diciembre 2025
