# User Impersonation Module for Odoo 17

## Descripción

Módulo que extiende `access_roles` para permitir a los administradores **impersonar** a otros usuarios, es decir, acceder al sistema como si fueran ese usuario sin necesidad de conocer su contraseña ni cerrar la sesión actual.

## Características Principales

### 🎭 Impersonación de Usuarios
- Botón "Impersonate User" en el formulario de usuario
- Solo visible para usuarios con permisos de impersonación
- No permite impersonarse a sí mismo ni al usuario administrador (uid=1)

### 🔒 Seguridad
- Nuevo grupo: **User Impersonation** (implica Settings/Administration/Settings)
- Solo usuarios autorizados pueden impersonar
- Control de acceso granular mediante grupos de seguridad

### 📊 Auditoría Completa
- Registro automático de todas las sesiones de impersonación
- Modelo `impersonate.log` con:
  - Usuario original
  - Usuario impersonado
  - Fecha/hora de inicio
  - Fecha/hora de fin
  - Duración de la sesión
- Vista de log accesible desde **Settings → Users & Companies → Impersonation Log**

### 🎨 Banner Visual
- Banner rojo destacado en la parte superior cuando estás impersonando
- Muestra:
  - Usuario que estás impersonando
  - Tu usuario original
  - Botón para detener la impersonación
- Animación suave al aparecer/desaparecer

## Instalación

1. Copia el módulo a tu directorio `addons/`:
   ```bash
   cp -r leulit_user_impersonate /path/to/odoo/addons/
   ```

2. Actualiza la lista de módulos en Odoo (Modo Desarrollador):
   - Apps → Update Apps List

3. Instala el módulo:
   - Busca "User Impersonation"
   - Haz clic en "Install"

## Dependencias

- `base` (Odoo core)
- `web` (Odoo web)
- `access_roles` (para gestión avanzada de permisos)

## Uso

### Impersonar un Usuario

**Opción A - Desde Access Role (más rápido)**:
1. Ve a **Access Role → Impersonar**
2. Verás un listado de usuarios disponibles
3. Haz clic en el botón **"Impersonate"** del usuario deseado
4. El sistema recargará y estarás viendo Odoo como ese usuario
5. Aparecerá un banner rojo en la parte superior

**Opción B - Desde Settings**:
1. Ve a **Settings → Users & Companies → Users**
2. Abre el formulario de un usuario
3. Haz clic en el botón **"Impersonate User"** (solo visible si tienes permisos)
4. El sistema recargará y estarás viendo Odoo como ese usuario
5. Aparecerá un banner rojo en la parte superior

### Detener la Impersonación

Hay dos formas:

1. **Desde el banner**: Haz clic en el botón "Stop Impersonation" en el banner rojo
2. **Automáticamente**: Cierra sesión normalmente

El sistema volverá a tu usuario original.

### Ver el Log de Auditoría

1. Ve a **Settings → Users & Companies → Impersonation Log**
2. Verás todas las sesiones de impersonación:
   - Filtro "Active Sessions": solo sesiones activas
   - Filtro "Today": sesiones de hoy
   - Agrupaciones por usuario, fecha, etc.

## Arquitectura Técnica

### Backend (Python)

#### Modelos
- **`res.users`** (heredado):
  - `is_impersonating`: campo computado
  - `can_impersonate`: campo computado
  - `action_impersonate_user()`: inicia impersonación
  - `action_stop_impersonation()`: detiene impersonación

- **`impersonate.log`**:
  - Registro de auditoría de sesiones
  - Campos: original_user_id, impersonated_user_id, start_date, end_date, duration

#### Controladores
- `/web/impersonate/start`: inicia sesión de impersonación
- `/web/impersonate/stop`: detiene sesión de impersonación
- `/web/impersonate/status`: verifica estado actual

### Frontend (JavaScript/OWL)

#### Componentes
- **`ImpersonationBanner`**: componente OWL registrado en systray
  - Se muestra solo cuando hay impersonación activa
  - Permite detener la impersonación con un clic

#### Client Actions
- `start_impersonation`: acción cliente para iniciar
- `stop_impersonation`: acción cliente para detener

## Seguridad

### Grupos
- `group_impersonate_user`: usuarios que pueden impersonar
  - Implica `base.group_system` (Settings)
  - Categoría: Administration

### Reglas de Seguridad
- Solo usuarios del grupo pueden acceder al modelo `impersonate.log`
- Los usuarios normales pueden ver el log (solo lectura)

### Restricciones
1. No puedes impersonarte a ti mismo
2. No puedes impersonar al usuario administrador (uid=1)
3. Solo usuarios con grupo `group_impersonate_user` pueden impersonar
4. Todas las sesiones quedan registradas en el log

## Casos de Uso

### 1. Testing de Permisos
Verifica qué puede ver y hacer un usuario específico sin necesidad de crear una cuenta de prueba o pedirle su contraseña.

### 2. Debugging
Reproduce problemas reportados por usuarios específicos viendo exactamente lo que ellos ven.

### 3. Auditoría de Acceso
Verifica que los permisos y roles estén configurados correctamente para diferentes tipos de usuarios.

### 4. Soporte
Ayuda a usuarios con problemas específicos viendo su pantalla exacta sin compartir pantalla.

### 5. Formación
Muestra a nuevos usuarios cómo se ve el sistema con diferentes roles.

## Integración con `access_roles`

Este módulo complementa perfectamente a `access_roles`:

1. **`access_roles`**: visualiza permisos y accesos de forma gráfica
2. **`leulit_user_impersonate`**: prueba esos permisos en vivo impersonando al usuario

Juntos proporcionan una solución completa para auditoría y testing de permisos.

## Notas Técnicas

### Gestión de Sesión
La impersonación funciona modificando el `uid` de la sesión HTTP:
```python
# Guarda el usuario original
request.session['impersonate_original_uid'] = original_uid
request.session['impersonate_target_uid'] = user_id

# Cambia al usuario objetivo
request.session.uid = user_id
```

### Persistencia
La sesión de impersonación persiste mientras:
- No cierres el navegador
- No hagas logout
- No hagas clic en "Stop Impersonation"

### Compatibilidad
- Odoo 17.0 Community y Enterprise
- Compatible con modo multi-empresa
- Compatible con todos los módulos estándar de Odoo

## Troubleshooting

### El botón "Impersonate User" no aparece
- Verifica que tu usuario tenga el grupo "User Impersonation"
- Verifica que no estés viendo tu propio formulario de usuario
- Verifica que no sea el usuario administrador (uid=1)

### El banner no aparece después de impersonar
- Limpia la caché del navegador (Ctrl+Shift+R)
- Verifica que los assets JS/CSS estén cargados correctamente
- Revisa la consola del navegador en busca de errores

### Error "Cannot impersonate yourself"
- No puedes impersonarte a ti mismo. Selecciona otro usuario.

### La impersonación no se detiene
- Usa el botón "Stop Impersonation" del banner
- O cierra sesión y vuelve a iniciar con tu usuario

## Desarrollo Futuro

Posibles mejoras:
- [ ] Límite de tiempo para sesiones de impersonación
- [ ] Notificación al usuario impersonado (opcional)
- [ ] Historial de acciones realizadas durante impersonación
- [ ] Restricción de qué usuarios pueden ser impersonados
- [ ] API REST para impersonación desde aplicaciones externas

## Licencia

LGPL-3

## Autor

**Helipistas**

## Soporte

Para soporte o reportar problemas, contacta al equipo de desarrollo.
