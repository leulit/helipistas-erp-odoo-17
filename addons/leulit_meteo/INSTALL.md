# Instalación de `leulit_meteo`

Guía de instalación, configuración inicial y verificación del módulo de meteorología para Odoo 17.

---

## 1. Requisitos previos

- **Odoo 17 Community** en funcionamiento.
- **Módulo `leulit`** instalado (dependencia interna del addon).
- **Python**: paquete `requests` disponible en el entorno donde corre Odoo. Si no lo está:

  ```bash
  pip install requests
  ```

- **Acceso a Internet** desde el servidor Odoo (consultas a Open-Meteo, Windy, AEMET, OpenAIP, CheckWX y aviationweather.gov) y desde el navegador del usuario (CDN `unpkg.com` para Leaflet).

No se requiere instalar Leaflet manualmente: el módulo lo declara vía CDN en sus assets.

---

## 2. Instalación del módulo

1. Copiar el directorio `leulit_meteo/` dentro de la ruta de addons de la instancia Odoo.
2. En Odoo, ir a **Aplicaciones**, pulsar **Actualizar lista de aplicaciones**.
3. Buscar **`leulit_meteo`** y pulsar **Instalar**.

Alternativa por línea de comandos:

```bash
odoo -u leulit_meteo -d <nombre_bd> --stop-after-init
```

Tras instalar/actualizar, refrescar el navegador con **Ctrl+F5** para asegurar que se cargan los assets nuevos (Leaflet, vistas).

---

## 3. Configuración inicial

Las API keys se gestionan en `Meteorología → Configuración → API Keys` (wizard `leulit.meteo.config`, solo administradores). Cada key tiene un botón **Validar** para comprobar la conectividad antes de guardar.

### 3.1. Windy API Key (opcional, recomendada para modelos profesionales)

Útil para consultar modelos meteorológicos profesionales (GFS, ECMWF, ICON, ICON-EU, NAM) y el mapa visual embebido de Windy.

1. Obtener la API key gratuita en <https://api.windy.com/keys>.
2. En Odoo: **Meteorología → Configuración → API Keys**.
3. Pegar la clave en **Windy API Key** y seleccionar el **modelo por defecto**.
4. Pulsar **Validar API Key** y luego **Guardar**.

Sin esta clave, las consultas con fuente "Windy" lanzarán un `UserError`.

### 3.2. AEMET OpenData API Key (recomendada para estaciones españolas)

Para descargar METAR + TAF + SIGMET oficiales de AEMET OpenData.

1. Solicitar la API key (JWT) gratuita en <https://opendata.aemet.es/centrodedescargas/altaUsuario>. Llega por correo electrónico.
2. En Odoo: **Meteorología → Configuración → API Keys**.
3. Pegar el JWT completo en **AEMET OpenData API Key** (son cadenas largas; copiar sin espacios ni saltos de línea).
4. Pulsar **Validar API Key** y luego **Guardar**.

> **Nota:** el RAW del METAR/TAF/SIGMET se guarda **sin modificación** (válido a efectos de AESA).

### 3.3. OpenAIP API Key (recomendada para auto-resolución de OACIs)

Usada para obtener coordenadas y nombre oficial de un aeródromo cuando se pide un briefing para un OACI no registrado en la tabla de referencia.

1. Registrarse en <https://www.openaip.net/> y obtener la API key.
2. En Odoo: **Meteorología → Configuración → API Keys**.
3. Pegar la clave en **OpenAIP API Key**.
4. Pulsar **Validar API Key** y luego **Guardar**.

Sin esta clave, la auto-resolución de OACIs desconocidos usa solo CheckWX para las coordenadas.

### 3.4. CheckWX API Key (opcional — solo para auto-resolución de OACIs desconocidos)

Usada para:
- Verificar si un OACI tiene METAR propio.
- Encontrar el aeródromo con METAR oficial más cercano (radio 150 km) cuando se auto-resuelve un OACI desconocido.

> **Nota:** la sincronización de aeródromos de referencia ya **no requiere** esta clave; el botón "Actualizar aeródromos de referencia" usa aviationweather.gov (NOAA/FAA, sin API key).

1. Registrarse en <https://www.checkwxapi.com/> y obtener la API key.
2. En Odoo: **Meteorología → Configuración → API Keys**.
3. Pegar la clave en **CheckWX API Key**.
4. Pulsar **Validar API Key** y luego **Guardar**.

Sin esta clave, la auto-resolución de OACIs desconocidos usará solo OpenAIP para las coordenadas y no podrá identificar el aeródromo con METAR más cercano.

### 3.5. Parámetros: cron y notificaciones de error

En `Meteorología → Configuración → Parámetros` (wizard `leulit.meteo.params`, solo administradores):

- **Actualización automática de METAR activa**: activa/desactiva el cron que descarga METAR/TAF de todos los aeródromos de referencia cada 10 minutos y los almacena en el histórico.
- **Email(s) para notificación de errores**: dirección(es) separadas por coma a las que se enviarán avisos si el cron encuentra errores. Si se deja vacío, no se envían notificaciones.
- **Actualizar aeródromos de referencia**: botón que consulta aviationweather.gov (NOAA/FAA, sin API key) para sincronizar la lista de aeródromos españoles LE*/GC* con METAR o TAF.

---

## 4. Verificación post-instalación

1. **Menús**: en la barra superior debe aparecer **Meteorología** con submenús:
   - Consultas Clima
   - Rutas Predefinidas
   - Reportes METAR
   - Aeródromos de Referencia (solo administradores)

2. **Open-Meteo (sin clave)**: en **Consultas Clima**, crear un registro nuevo, introducir coordenadas (por ejemplo Madrid: `40.4168, -3.7038`) y pulsar **Consultar Clima Actual**. Debe devolver datos en pocos segundos.

3. **AEMET (si se configuró)**: en **Reportes METAR**, crear un registro con OACI `LEMD` (proveedor por defecto: AEMET) y pulsar **Obtener briefing**. Debe rellenarse el RAW del METAR, el TAF y los SIGMET vigentes para la FIR LECM.

4. **Auto-resolución**: en **Reportes METAR**, pedir briefing de un OACI que no esté en la tabla de referencia (con OpenAIP y CheckWX configurados). El sistema debe crear automáticamente el registro en **Aeródromos de Referencia** y devolver el METAR del aeródromo cercano.

5. **Windy (si se configuró)**: abrir una consulta existente, cambiar **Fuente de Datos** a **Windy** y pulsar **Consultar Windy**. Deben llegar los datos del modelo seleccionado.

---

## 5. Limitaciones conocidas

- **Sin caché en consultas manuales**: cada acción de usuario consulta la API en directo. El cron sí almacena en `leulit.meteo.historico`.
- **Aeródromos de Referencia**: la tabla se puede sembrar manualmente o mediante la sincronización desde CheckWX. Para añadir helipuertos sin METAR propio de forma manual, edítela desde **Meteorología → Aeródromos de Referencia** (solo administradores).
- **Open-Meteo**: aunque su uso es libre y sin clave, mantiene límites suaves para uso comercial intensivo.
- **Auto-resolución sin coordenadas**: si no se dispone de OpenAIP ni CheckWX key y el OACI no está en la tabla, no se puede determinar el aeródromo de referencia automáticamente.

---

## 6. Troubleshooting

### El mapa Leaflet no aparece en el formulario
- El navegador necesita poder cargar recursos desde **`unpkg.com`** (CDN de Leaflet). Verificar que no esté bloqueado por proxy/firewall.
- Forzar recarga con **Ctrl+F5** para refrescar los assets.
- Revisar la consola del navegador (F12) por errores de carga.

### "No se ha configurado la API Key de AEMET"
Ir a **Meteorología → Configuración → API Keys** y pegar el JWT de AEMET (sección 3.2).

### "La API Key de AEMET no es válida"
- Comprobar que la JWT está completa, sin espacios ni saltos de línea (son cadenas largas).
- Las claves recién emitidas pueden tardar unos minutos en activarse en el servicio de AEMET. Esperar y reintentar.

### "No se han podido obtener datos de AEMET para …"
AEMET puede no estar publicando METAR/TAF para ese OACI en este momento (aeródromo cerrado, sin servicio MET). Si el OACI corresponde a un helipuerto sin METAR propio, asegúrese de que está dado de alta en **Aeródromos de Referencia** con `tiene_metar_propio = False` y un `ref_icao` correcto.

### "API Key de Windy no válida"
- Comprobar que la clave se ha copiado entera y sin espacios.
- Las claves recién emitidas pueden tardar minutos en activarse.
- Revisar los límites de uso de la cuenta Windy.

### El cron no genera histórico
- Verificar que el cron está activo en **Meteorología → Configuración → Parámetros**.
- Comprobar en **Técnico → Acciones planificadas** que `Actualizar METAR Aeródromos de Referencia` no tiene errores en su última ejecución.
- Revisar que la tabla de Aeródromos de Referencia tiene registros con `proxima_actualizacion` nula o pasada.
