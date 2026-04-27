# Instalación de `leulit_meteo`

Guía de instalación, configuración inicial y verificación del módulo de meteorología para Odoo 16.

---

## 1. Requisitos previos

- **Odoo 16 Community** en funcionamiento.
- **Módulo `leulit`** instalado (dependencia interna del addon).
- **Python**: paquete `requests` disponible en el entorno donde corre Odoo. Si no lo está:

  ```bash
  pip install requests
  ```

- **Acceso a Internet** desde el servidor Odoo (consultas a Open-Meteo, Windy y AEMET) y desde el navegador del usuario (CDN `unpkg.com` para Leaflet).

No se requiere instalar Leaflet manualmente: el módulo lo declara vía CDN en sus assets.

---

## 2. Instalación del módulo

1. Copiar el directorio `leulit_meteo/` dentro de la ruta de addons de la instancia Odoo.
2. En Odoo, ir a **Aplicaciones**, pulsar **Actualizar lista de aplicaciones**.
3. Buscar **`leulit_meteo`** y pulsar **Instalar**.

Alternativa por línea de comandos (genérica, sin asumir Docker):

```bash
odoo -u leulit_meteo -d <nombre_bd> --stop-after-init
```

Tras instalar/actualizar, refrescar el navegador con **Ctrl+F5** para asegurar que se cargan los assets nuevos (Leaflet, vistas).

---

## 3. Configuración inicial

Ambas API keys son **opcionales**, pero recomendadas según el uso previsto. Sin ninguna de ellas, el módulo sigue funcionando contra **Open-Meteo** (sin clave).

### 3.1. Windy API Key (opcional, recomendada para modelos profesionales)

Útil si se quieren consultar modelos meteorológicos profesionales (GFS, ECMWF, ICON, ICON-EU, NAM) o usar el mapa visual embebido de Windy.

1. Obtener la API key gratuita en <https://api.windy.com/keys>.
2. En Odoo: **Meteorología → Configuración** (submenú restringido a administradores — `base.group_system`). Se abre como modal (wizard).
3. Pegar la clave en **Windy API Key**.
4. Seleccionar el **modelo por defecto** (GFS, ECMWF, ICON, ICON-EU o NAM).
5. Pulsar **Validar API Key** y luego **Guardar**.

Sin esta clave, las consultas con fuente "Windy" lanzarán un `UserError`. Open-Meteo seguirá funcionando con normalidad.

### 3.2. AEMET OpenData API Key (opcional, recomendada para estaciones españolas)

Útil para construir partes tipo METAR a partir de observaciones horarias de estaciones AEMET en España.

1. Solicitar la API key (un JWT) gratuita en <https://opendata.aemet.es/centrodedescargas/altaUsuario>. Llega por correo electrónico.
2. En Odoo: **Meteorología → Configuración**.
3. Pegar el JWT completo en **AEMET OpenData API Key** (las JWT son largas; copiar sin espacios ni saltos de línea).
4. Pulsar **Validar API Key** y luego **Guardar**.

Sin esta clave, la acción **Obtener observación** del modelo `leulit.meteo.metar` (con proveedor AEMET seleccionado) lanzará `UserError`.

> **Nota:** AEMET OpenData **no** publica METAR oficiales. El módulo construye un texto en formato tipo METAR a partir de la observación horaria de la estación; el resultado queda etiquetado con `RMK AEMET` para diferenciarlo.

---

## 4. Verificación post-instalación

1. **Menús**: en la barra superior debe aparecer **Meteorología** con tres submenús:
   - Consultas Clima
   - Rutas Predefinidas
   - Reportes METAR

2. **Open-Meteo (sin clave)**: en **Consultas Clima**, crear un registro nuevo, introducir coordenadas (por ejemplo Madrid: `40.4168, -3.7038`) y pulsar **Consultar Clima Actual**. Debe devolver datos en pocos segundos.

3. **AEMET (si se configuró)**: en **Reportes METAR**, crear un registro con OACI `LEMD` (proveedor por defecto: AEMET) y pulsar **Obtener observación**. Debe rellenarse el texto tipo METAR con el sufijo `RMK AEMET`.

4. **Windy (si se configuró)**: abrir una consulta existente, cambiar **Fuente de Datos** a **Windy** y pulsar **Consultar Windy**. Deben llegar los datos del modelo seleccionado.

---

## 5. Limitaciones conocidas

- **Sin caché**: cada acción consulta la API en directo. No hay almacenamiento intermedio.
- **Resolución OACI → IDEMA en AEMET**: existe un mapa estático con ~30 aeropuertos y aeródromos españoles habituales. Para estaciones no incluidas, introducir manualmente el código de estación (IDEMA) en el formulario.
- **Open-Meteo**: aunque su uso es libre y sin clave, mantiene límites suaves para uso comercial intensivo.

---

## 6. Troubleshooting

### El mapa Leaflet no aparece en el formulario
- El navegador necesita poder cargar recursos desde **`unpkg.com`** (CDN de Leaflet). Verificar que no esté bloqueado por proxy/firewall.
- Forzar recarga con **Ctrl+F5** para refrescar los assets.
- Revisar la consola del navegador (F12) por errores de carga.

### "No se ha configurado la API Key de AEMET"
Ir a **Meteorología → Configuración** y pegar el JWT de AEMET (sección 3.2).

### "La API Key de AEMET no es válida"
- Comprobar que la JWT está completa, sin espacios ni saltos de línea (son cadenas largas).
- Las claves recién emitidas pueden tardar unos minutos en activarse en el servicio de AEMET. Esperar y reintentar.

### "No se han podido obtener datos de AEMET para …"
La estación AEMET asociada al ICAO puede no tener observación reciente disponible. Probar con otro código de estación conocido o con el aeropuerto/aeródromo más cercano que sí publique observación horaria.

### "API Key de Windy no válida"
- Comprobar que la clave se ha copiado entera y sin espacios.
- Las claves recién emitidas pueden tardar minutos en activarse.
- Revisar los límites de uso de la cuenta Windy.
