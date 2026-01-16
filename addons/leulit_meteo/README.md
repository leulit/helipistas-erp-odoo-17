# Leulit Meteorología

Módulo de integración con Open-Meteo y Aviation Weather para obtener información meteorológica en tiempo real.

## Características

- ☁️ **Consulta de Clima Actual**: Obtén temperatura, humedad, precipitación y viento (Open-Meteo)
- 📅 **Pronósticos**: Consulta pronósticos meteorológicos hasta 16 días (Open-Meteo)
- ✈️ **Reportes METAR**: Obtén reportes meteorológicos aeronáuticos oficiales (Aviation Weather)
- 🛩️ **Categorías de Vuelo**: Clasificación automática VFR/MVFR/IFR/LIFR
- 📍 **Múltiples Ubicaciones**: Registra y consulta clima de diferentes ubicaciones
- 🔗 **Integración**: Vincula consultas con vuelos u otras operaciones
- 📊 **Histórico**: Mantén un registro de todas las consultas realizadas

## APIs Utilizadas

### 1. Open-Meteo (Clima General)
[Open-Meteo](https://open-meteo.com/) - API meteorológica gratuita y de código abierto.
- Datos meteorológicos globales
- Sin autenticación requerida
- Sin límites de uso

### 2. Aviation Weather (METAR)
[Aviation Weather Center](https://aviationweather.gov/) - API oficial de datos meteorológicos aeronáuticos.
- Reportes METAR en tiempo real
- Datos TAF (Terminal Aerodrome Forecast)
- Categorías de vuelo (VFR/IFR)
- Sin autenticación requerida

### Datos Disponibles

**Open-Meteo (Clima General):**
- Temperatura actual y sensación térmica
- Humedad relativa
- Precipitación
- Cobertura de nubes
- Velocidad y dirección del viento
- Rachas de viento
- Códigos de condiciones meteorológicas WMO

**Aviation Weather (METAR):**
- Reporte METAR completo en texto
- Temperatura y punto de rocío
- Viento (dirección, velocidad, rachas)
- Visibilidad
- QNH / Altímetro
- Categoría de vuelo (VFR/MVFR/IFR/LIFR)
- Información de nubes
- Fenómenos meteorológicos (lluvia, niebla, etc.)

## Instalación

### Dependencias Python

```bash
pip install requests
```

O en Docker:

```bash
docker exec -ti helipistas_odoo pip install requests
```

### Instalación del Módulo

1. Actualizar lista de aplicaciones
2. Buscar "Leulit Meteorología"
3. Hacer clic en "Instalar"

## Uso

### Crear una Consulta

1. Ir a **Meteorología > Consultas**
2. Hacer clic en **Crear**
3. Introducir:
   - Ubicación (ej: "Madrid - LECU")
   - Latitud (ej: 40.3717)
   - Longitud (ej: -3.7856)
4. Hacer clic en **Consultar Clima Actual** o **Obtener Pronóstico**

### Obtener un METAR

1. Ir a **Meteorología > Reportes METAR**
2. Hacer clic en **Crear**
3. Introducir código OACI (4 letras): **LECU**
4. Hacer clic en **Obtener METAR**
5. Ver reporte completo y datos decodificados

**⚠️ Nota Importante - Datos Históricos**: Los METAR son reportes históricos. La vista muestra el estado del momento en que se consultó la API, no datos en tiempo real. Para actualizar:
- Abrir el registro existente
- Hacer clic en **Obtener METAR** nuevamente
- Los datos se actualizarán con el METAR más reciente
- El campo `observation_time` indica cuándo se realizó la observación
- El campo `fecha_consulta` indica cuándo se consultó desde Odoo

### Categorías de Vuelo METAR

- **VFR** (Verde): Techo > 5000ft, Visibilidad > 5mi
- **MVFR** (Amarillo): Techo 3000-5000ft, Visibilidad 3-5mi
- **IFR** (Naranja): Techo 1000-3000ft, Visibilidad 1-3mi
- **LIFR** (Rojo): Techo < 1000ft, Visibilidad < 1mi

### Integración con Otros Módulos

Puedes llamar al servicio desde otros módulos:

### Consultar Clima (Open-Meteo)

```python
# Consultar clima desde cualquier módulo
meteo = self.env['leulit.meteo.consulta']
datos = meteo.consultar_clima_ubicacion(
    ubicacion='Madrid LECU',
    latitud=40.3717,
    longitud=-3.7856
)

if datos:
    temperatura = datos['temperatura']
    viento = datos['viento']
    descripcion = datos['descripcion']
```

### Obtener METAR Aeronáutico

```python
# Obtener METAR de un aeródromo
metar_obj = self.env['leulit.meteo.metar']
datos_metar = metar_obj.obtener_metar_aerodromo('LECU')

if datos_metar:
    metar_id = datos_metar['metar_id']
    raw = datos_metar['raw']
    temperatura = datos_metar['temperatura']
    viento = datos_metar['viento_velocidad']
    qnh = datos_metar['qnh']
    categoria = datos_metar['categoria_vuelo']  # VFR, MVFR, IFR, LIFR
```

### Ejemplo Integración con Vuelos

```python
# En leulit_operaciones
class LeulitVuelo(models.Model):
    _inherit = 'leulit.vuelo'
    
    metar_id = fields.Many2one('leulit.meteo.metar', string='METAR')
    
    def action_obtener_metar_salida(self):
        if self.aerodromo_salida_id.codigo_oaci:
            metar_obj = self.env['leulit.meteo.metar']
            datos = metar_obj.obtener_metar_aerodromo(
                self.aerodromo_salida_id.codigo_oaci
            )
            if datos:
                self.metar_id = datos['metar_id']
```

## Ejemplos de Ubicaciones

### Aeródromos Españoles

| Ubicación | Latitud | Longitud |
|-----------|---------|----------|
| Madrid - Cuatro Vientos (LECU) | 40.3717 | -3.7856 |
| Sabadell (LELL) | 41.5209 | 2.1050 |
| Granada - Armilla (LEGA) | 37.1331 | -3.6356 |
| Valencia (LEVC) | 39.4893 | -0.4816 |
| Sevilla (LEZL) | 37.4180 | -5.8931 |

## Notas Técnicas

- **Sin límites de rate**: Open-Meteo es gratuito y no requiere API key
- **Caché**: Considera implementar caché para evitar consultas repetidas
- **Timeout**: Las consultas tienen un timeout de 10 segundos
- **Errores**: Los errores se registran en el log de Odoo

## Soporte

Para más información sobre los datos disponibles, consulta la documentación oficial de Open-Meteo:
https://open-meteo.com/en/docs

## Autor

**Leulit**  
https://www.leulit.com

## Licencia

LGPL-3
