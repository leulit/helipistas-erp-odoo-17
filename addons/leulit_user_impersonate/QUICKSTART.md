# Guía Rápida - Módulo de Impersonación de Usuarios

## 📦 Instalación Rápida

### Opción 1: Script Automático (Recomendado)
```bash
cd /Users/emiloalvarez/Work/PROYECTOS/HELIPISTAS/ODOO-17-2025/ERP-ODOO/addons/leulit_user_impersonate
./install_impersonate.sh
```

### Opción 2: Manual con Docker
```bash
docker exec -ti helipistas_odoo_17 odoo -i leulit_user_impersonate -d productiu --stop-after-init
```

### Opción 3: Desde la Interfaz de Odoo
1. Activa el modo desarrollador
2. Ve a **Apps**
3. Actualiza lista de aplicaciones
4. Busca "User Impersonation"
5. Haz clic en **Instalar**

---

## 🚀 Uso Básico

### 1️⃣ Asignar Permisos

**Paso 1**: Ve a Settings → Users & Companies → Users

**Paso 2**: Abre tu usuario (o el usuario que quieres autorizar)

**Paso 3**: En la pestaña "Access Rights", busca y activa:
- ✅ **Administration / Settings** (si no lo tiene ya)
- ✅ **User Impersonation** (nuevo grupo del módulo)

**Paso 4**: Guarda los cambios

### 2️⃣ Impersonar un Usuario

**Método A - Desde Access Role (Recomendado)**:

**Paso 1**: Ve a **Access Role → Impersonar**

**Paso 2**: Verás un listado de todos los usuarios disponibles

**Paso 3**: Haz clic en el botón **"Impersonate"** (azul) del usuario que quieres

**Paso 4**: Espera a que la página recargue

**Método B - Desde Settings**:

**Paso 1**: Ve a Settings → Users & Companies → Users

**Paso 2**: Abre el formulario del usuario que quieres impersonar

**Paso 3**: Haz clic en el botón **"Impersonate User"** (naranja, arriba)

**Paso 4**: Espera a que la página recargue

✅ **¡Listo!** Ahora estás viendo Odoo como ese usuario. Verás un **banner rojo** en la parte superior.

### 3️⃣ Detener la Impersonación

**Opción A**: Haz clic en el botón **"Stop Impersonation"** del banner rojo

**Opción B**: Cierra sesión normalmente

✅ Volverás a tu usuario original automáticamente.

---

## 🎯 Ejemplos de Uso Práctico

### Caso 1: Verificar Permisos de un Piloto
```
1. Impersona al piloto
2. Ve a "Operaciones"
3. Verifica qué menús puede ver
4. Intenta crear un vuelo
5. Verifica si puede editarlo
6. Stop impersonation
```

### Caso 2: Debugging de un Problema Reportado
```
Usuario dice: "No puedo ver mis vuelos"

1. Impersona a ese usuario
2. Navega a donde debería ver sus vuelos
3. Reproduce el problema
4. Identifica qué falta (permisos, filtros, etc.)
5. Stop impersonation
6. Corrige el problema
```

### Caso 3: Auditoría de Seguridad
```
1. Impersona a un usuario "Alumno"
2. Verifica que NO puede acceder a:
   - CAMO
   - Taller
   - Configuración
3. Verifica que SÍ puede acceder a:
   - Escuela
   - Sus propios partes
4. Stop impersonation
5. Documenta los accesos
```

---

## 📊 Ver el Log de Auditoría

### Acceder al Log
**Settings → Users & Companies → Impersonation Log**

### Filtros Útiles
- **Active Sessions**: ver quién está impersonando ahora mismo
- **Today**: sesiones de hoy
- **Group by Original User**: ver quién ha impersonado
- **Group by Impersonated User**: ver quién ha sido impersonado

### Información del Log
Cada registro muestra:
- 👤 **Usuario Original**: quién inició la impersonación
- 🎭 **Usuario Impersonado**: a quién se impersonó
- 🕐 **Inicio**: cuándo empezó
- 🕑 **Fin**: cuándo terminó (vacío si está activa)
- ⏱️ **Duración**: cuánto duró

---

## 🔒 Seguridad y Restricciones

### ✅ Permitido
- Impersonar cualquier usuario excepto:
  - A ti mismo
  - Al usuario administrador (uid=1)
- Ver todo lo que el usuario impersonado puede ver
- Hacer todo lo que el usuario impersonado puede hacer

### ❌ NO Permitido
- Impersonarte a ti mismo (sin sentido)
- Impersonar al admin (por seguridad)
- Impersonar sin tener el grupo "User Impersonation"
- Modificar la contraseña del usuario impersonado

### 🔍 Trazabilidad
- **Todas las sesiones** quedan registradas
- Se registra **quién, cuándo, a quién** y **cuánto tiempo**
- Los logs **no se pueden borrar** (excepto admin)
- Se puede auditar retrospectivamente

---

## 🎨 Interfaz Visual

### Banner de Impersonación
Cuando estás impersonando verás:

```
┌─────────────────────────────────────────────────────────┐
│ 🕵️ Impersonating: Juan Pérez                           │
│    (Original user: Admin)         [Stop Impersonation] │
└─────────────────────────────────────────────────────────┘
```

**Características**:
- ❤️ Color rojo llamativo (imposible ignorar)
- 🔁 Animación suave al aparecer
- 👤 Muestra ambos usuarios (original y objetivo)
- 🛑 Botón de stop siempre visible
- 📱 Responsive (funciona en móvil)

---

## 🛠️ Troubleshooting

### Problema: No veo el botón "Impersonate User"
**Solución**:
1. Verifica que tienes el grupo "User Impersonation"
2. Asegúrate de no estar viendo tu propio formulario
3. Verifica que no es el usuario admin (uid=1)
4. Recarga la página (Ctrl+R)

### Problema: El banner no aparece
**Solución**:
1. Limpia caché: Ctrl+Shift+R (hard reload)
2. Verifica en DevTools que los JS/CSS están cargados
3. Revisa la consola del navegador (F12)
4. Reinicia Odoo: `docker restart helipistas_odoo_17`

### Problema: Error "Cannot impersonate yourself"
**Causa**: Estás intentando impersonarte a ti mismo.
**Solución**: Selecciona otro usuario diferente.

### Problema: La sesión no se cierra
**Solución**:
1. Usa el botón "Stop Impersonation"
2. Si falla, cierra sesión manualmente
3. Si persiste, limpia cookies del navegador
4. Como último recurso, reinicia el contenedor Docker

### Problema: "You are not allowed to impersonate users"
**Causa**: No tienes el grupo necesario.
**Solución**:
1. Pide a un admin que te añada al grupo
2. O usa el usuario admin para hacerlo tú mismo

---

## 🔧 Comandos Útiles

### Actualizar el Módulo
```bash
docker exec -ti helipistas_odoo_17 odoo -u leulit_user_impersonate -d productiu --stop-after-init
```

### Ver Logs en Tiempo Real
```bash
docker logs -f helipistas_odoo_17 | grep -i impersonate
```

### Reiniciar Odoo
```bash
docker restart helipistas_odoo_17
```

### Acceder a Shell de Odoo
```bash
docker exec -ti helipistas_odoo_17 odoo shell -d productiu
```

Luego en el shell:
```python
# Ver usuarios con permiso de impersonación
users = env['res.users'].search([])
for user in users:
    if user.has_group('leulit_user_impersonate.group_impersonate_user'):
        print(f"{user.name} - {user.login}")

# Ver log de impersonaciones
logs = env['impersonate.log'].search([], order='start_date desc', limit=10)
for log in logs:
    print(f"{log.original_user_id.name} -> {log.impersonated_user_id.name} ({log.duration})")
```

---

## 📖 Integración con access_roles

Este módulo complementa perfectamente a `access_roles`:

| Módulo | Función | Uso |
|--------|---------|-----|
| **access_roles** | Visualiza permisos | "¿Qué permisos tiene Juan?" |
| **leulit_user_impersonate** | Prueba permisos | "Veamos qué ve Juan realmente" |

**Workflow recomendado**:
1. Usa `access_roles` para revisar permisos teóricos
2. Usa `leulit_user_impersonate` para probar permisos reales
3. Ajusta roles según hallazgos
4. Vuelve a probar con impersonación

---

## 📞 Soporte

Si tienes problemas:
1. Revisa esta guía completa
2. Consulta el [README.md](README.md) técnico
3. Revisa los [ejemplos.py](examples.py) de código
4. Contacta al equipo de desarrollo

---

## ✨ Características Avanzadas (Futuro)

Ideas para próximas versiones:
- ⏱️ Límite de tiempo automático (auto-cerrar después de X minutos)
- 📧 Notificación al usuario impersonado (opcional)
- 📜 Log de acciones realizadas durante impersonación
- 🎯 Restricción de qué usuarios pueden ser impersonados
- 🌐 API REST para impersonación desde apps externas
- 📊 Dashboard de estadísticas de impersonación

---

**Versión**: 1.0.0  
**Fecha**: Diciembre 2024  
**Autor**: Helipistas  
**Licencia**: LGPL-3
