# Integración METAR/TAF con el Parte de Vuelo (`leulit_vuelo`)

Este documento muestra cómo vincular la consulta meteorológica automática al parte de vuelo del módulo `leulit_vuelo`. El objetivo es que cada parte de vuelo quede enlazado con el METAR/TAF vigente en el momento de su autorización, a efectos operacionales y de trazabilidad AESA.

---

## 1. Modelo — añadir el campo METAR al parte de vuelo

```python
# addons/leulit_vuelo/models/leulit_vuelo.py

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class LeulitVuelo(models.Model):
    _inherit = 'leulit.vuelo'

    metar_salida_id = fields.Many2one(
        'leulit.meteo.metar',
        string='Meteorología (salida)',
        readonly=True,
        help='METAR/TAF registrado en el momento de la autorización del vuelo.')

    estado_meteo = fields.Selection(
        [('ok', 'Condiciones aceptables'),
         ('marginal', 'Condiciones marginales'),
         ('nogo', 'Por debajo de mínimos'),
         ('sin_datos', 'Sin datos meteorológicos')],
        string='Estado meteorológico',
        compute='_compute_estado_meteo',
        store=True)

    @api.depends('metar_salida_id.wind_speed_kt',
                 'metar_salida_id.wind_gust_kt',
                 'metar_salida_id.visibility_m')
    def _compute_estado_meteo(self):
        from odoo.addons.leulit_meteo.models.leulit_meteo_umbral_config import LeulitMeteoUmbralConfig
        u = LeulitMeteoUmbralConfig.get_umbrales(self.env)
        for vuelo in self:
            metar = vuelo.metar_salida_id
            if not metar or not metar.raw_metar:
                vuelo.estado_meteo = 'sin_datos'
                continue
            viento = metar.wind_speed_kt or 0
            rachas = metar.wind_gust_kt or 0
            visibilidad = metar.visibility_m or 0
            if viento > u['viento_nogo'] or rachas > u['rachas_nogo'] or visibilidad < u['vis_nogo']:
                vuelo.estado_meteo = 'nogo'
            elif viento > u['viento_marginal'] or rachas > u['rachas_marginal'] or visibilidad < u['vis_marginal']:
                vuelo.estado_meteo = 'marginal'
            else:
                vuelo.estado_meteo = 'ok'

    def action_obtener_meteo_salida(self):
        """Obtiene el METAR/TAF del aeródromo de salida y lo vincula al parte."""
        for vuelo in self:
            icao = (
                vuelo.aerodromo_salida_id.codigo_oaci
                if vuelo.aerodromo_salida_id
                else None
            )
            if not icao:
                raise UserError(_('El aeródromo de salida no tiene código OACI configurado.'))

            data = self.env['leulit.meteo.metar'].obtener_metar(
                icao_code=icao,
                provider='aemet',
                persistir=True,
            )
            if not data:
                raise UserError(_(
                    'No se pudo obtener información meteorológica para %s. '
                    'Verifique la conexión y la configuración del proveedor.'
                ) % icao)

            vuelo.metar_salida_id = data['record_id']

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Meteorología actualizada'),
                'message': _('METAR/TAF obtenido para %s') % icao,
                'type': 'success',
                'sticky': False,
            },
        }
```

---

## 1.1 API simplificada: `briefing_oaci`

`briefing_oaci` es el punto de entrada recomendado cuando otro módulo necesita obtener el briefing de un OACI y recibir directamente los tres campos que muestra el formulario: METAR oficial, TAF oficial y METAR sintético de la estación más cercana.

### Firma

```python
self.env['leulit.meteo.metar'].briefing_oaci(icao_code, provider='aemet', fecha=None)
```

| Parámetro | Tipo | Requerido | Descripción |
|---|---|---|---|
| `icao_code` | `str` | Sí | Código OACI de 4 letras (`LEUL`, `LEMD`, …) |
| `provider` | `str` | No | Proveedor a usar **si se crea** el registro. Por defecto `'aemet'`. Ignorado en modo histórico. |
| `fecha` | `datetime` UTC | No | Si se indica y está a más de 30 min en el pasado, activa el **modo histórico** (ver más abajo). |

### Valor de retorno

```python
{
    'record_id':      42,             # id del registro leulit.meteo.metar
    'raw_metar':      'LEUL ...',     # pestaña METAR del formulario
    'raw_taf':        'TAF ...',      # pestaña TAF del formulario
    'raw_metar_est':  'LEUL ...',     # METAR no oficial — estación más próxima
                                      # (None si el proveedor no lo incluye)
    'historico':      False,          # True si los datos vienen de BD sin actualizar
    'observation_time': datetime(...) # hora UTC de la observación
}
# → None si no hay datos disponibles
```

### Modo actual (sin `fecha`)

```
1. Busca el registro activo más reciente con icao_code = OACI
2. Si no existe → lo crea (con el proveedor indicado)
3. Llama al proveedor y escribe los datos (igual que el botón "Obtener briefing")
4. Devuelve los campos + historico=False
```

### Modo histórico (con `fecha` > 30 min en el pasado)

Las APIs de AEMET y CheckWX **no proporcionan datos históricos** — solo devuelven el METAR en vigor en el momento de la llamada. En modo histórico la función **solo consulta la base de datos**:

```
1. Busca el registro con observation_time más cercano a fecha (hacia atrás primero)
2. Si la diferencia supera 2 horas → devuelve None (registro demasiado alejado)
3. Si lo encuentra → devuelve sus datos + historico=True sin llamar a la API
```

> El histórico solo tiene datos si en su momento se guardaron registros con `persistir=True`
> o mediante el botón "Obtener briefing" del formulario.

### Ejemplo mínimo

```python
# Datos actuales
result = self.env['leulit.meteo.metar'].briefing_oaci('LEUL')
if result:
    _logger.info("METAR: %s", result['raw_metar'])
    _logger.info("TAF:   %s", result['raw_taf'])

# Datos de un vuelo anterior
from datetime import datetime
result = self.env['leulit.meteo.metar'].briefing_oaci(
    'LEUL', fecha=datetime(2026, 4, 27, 14, 30))
if result:
    _logger.info("Histórico: %s | Observación: %s",
                 result['historico'], result['observation_time'])
elif result is None:
    _logger.warning("Sin datos históricos para LEUL en esa fecha")
```

### Integración en el parte de vuelo (versión simplificada)

Reemplaza el uso de `obtener_metar` de la sección 1 por `briefing_oaci` para obtener un código más directo:

```python
def action_obtener_meteo_salida(self):
    for vuelo in self:
        icao = (
            vuelo.aerodromo_salida_id.codigo_oaci
            if vuelo.aerodromo_salida_id
            else None
        )
        if not icao:
            raise UserError(_('El aeródromo de salida no tiene código OACI configurado.'))

        result = self.env['leulit.meteo.metar'].briefing_oaci(icao)
        if not result:
            raise UserError(_(
                'No se pudo obtener información meteorológica para %s. '
                'Verifique la conexión y la configuración del proveedor.'
            ) % icao)

        vuelo.metar_salida_id = result['record_id']
        # result['raw_metar'], result['raw_taf'], result['raw_metar_est']
        # disponibles si se necesitan en el mismo flujo

    return {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': _('Meteorología actualizada'),
            'message': _('Briefing obtenido para %s') % icao,
            'type': 'success',
            'sticky': False,
        },
    }
```

### Cuándo usar cada función

| Función | Úsala cuando… |
|---|---|
| `briefing_oaci(icao)` | Quieres el briefing listo para mostrar (METAR + TAF + est.) y reutilizar el registro existente |
| `obtener_metar(icao, persistir=True)` | Necesitas el dict completo del proveedor (todos los campos numéricos, coordenadas, etc.) o quieres crear siempre un registro nuevo |

---

## 2. Vista — botón y campos meteorológicos en el parte de vuelo

```xml
<!-- addons/leulit_vuelo/views/leulit_vuelo_views.xml -->
<!-- Añadir dentro del form view de leulit.vuelo -->

<header>
    <!-- ... botones existentes ... -->
    <button name="action_obtener_meteo_salida"
            string="Obtener meteorología"
            type="object"
            class="btn-secondary"
            icon="fa-cloud-download"
            attrs="{'invisible': [('aerodromo_salida_id', '=', False)]}"/>
</header>

<!-- Añadir una página o grupo en el form -->
<page string="Meteorología" name="page_meteo">
    <group>
        <field name="estado_meteo" widget="badge"
               decoration-success="estado_meteo == 'ok'"
               decoration-warning="estado_meteo == 'marginal'"
               decoration-danger="estado_meteo in ('nogo', 'sin_datos')"/>
    </group>

    <group string="METAR / TAF de salida" attrs="{'invisible': [('metar_salida_id', '=', False)]}">
        <field name="metar_salida_id" readonly="1"/>
        <field name="metar_salida_id.observation_time" string="Hora observación (UTC)" readonly="1"/>
        <field name="metar_salida_id.edad_datos_minutos" string="Antigüedad (min)" readonly="1"/>
        <field name="metar_salida_id.estado_datos" string="Frescura" readonly="1"/>
        <field name="metar_salida_id.wind_direction" string="Viento dirección (°)" readonly="1"/>
        <field name="metar_salida_id.wind_speed_kt" string="Viento velocidad (kt)" readonly="1"/>
        <field name="metar_salida_id.wind_gust_kt" string="Rachas (kt)" readonly="1"/>
        <field name="metar_salida_id.visibility_m" string="Visibilidad (m)" readonly="1"/>
        <field name="metar_salida_id.qnh" string="QNH (hPa)" readonly="1"/>
        <field name="metar_salida_id.temperatura" string="Temperatura (°C)" readonly="1"/>
    </group>

    <group string="Textos oficiales" attrs="{'invisible': [('metar_salida_id', '=', False)]}">
        <field name="metar_salida_id.raw_metar" string="METAR" readonly="1" widget="text"/>
        <field name="metar_salida_id.raw_taf" string="TAF" readonly="1" widget="text"/>
        <field name="metar_salida_id.raw_sigmet" string="SIGMET" readonly="1" widget="text"/>
    </group>
</page>
```

---

## 3. Automatización — obtener meteorología al autorizar el vuelo

Si el parte de vuelo tiene un estado de autorización, se puede disparar la consulta meteorológica automáticamente al cambiar de estado:

```python
def action_autorizar_vuelo(self):
    """Autoriza el vuelo y captura automáticamente la meteorología."""
    self.ensure_one()
    # Obtener met antes de autorizar (sin lanzar error si falla — el piloto lo reintenta)
    try:
        self.action_obtener_meteo_salida()
    except Exception:
        pass  # La autorización no bloquea aunque met falle
    self.write({'state': 'autorizado'})
```

---

## 4. Permisos necesarios

En `security/ir.model.access.csv` de `leulit_vuelo`, asegurarse de que el perfil de piloto/operaciones tiene acceso de lectura a `leulit.meteo.metar`:

```csv
access_leulit_meteo_metar_vuelo_user,leulit.meteo.metar vuelo user,model_leulit_meteo_metar,leulit_vuelo.group_vuelo_user,1,0,0,0
```

---

## 5. Dependencia en `__manifest__.py`

```python
# addons/leulit_vuelo/__manifest__.py
{
    ...
    'depends': ['leulit_vuelo_base', 'leulit_meteo'],
    ...
}
```

---

## 6. Resultado para el auditor AESA

Con esta integración, cada parte de vuelo almacena:

| Campo | Valor ejemplo | Significado |
|---|---|---|
| `metar_salida_id` | METAR-0042 | Referencia al registro meteorológico |
| `estado_meteo` | `ok` | Evaluación automática respecto a umbrales del OM |
| `raw_metar` | `LELL 271430Z 12009KT CAVOK 23/12 Q1017` | Texto oficial sin alterar |
| `observation_time` | 27/04/2026 14:30 UTC | Hora de la observación |
| `fecha_consulta` | 27/04/2026 15:05 UTC | Momento en que se solicitó |
| `edad_datos_minutos` | 35 min | Frescura en el momento de la autorización |

Esto permite demostrar ante AESA que **existió una consulta meteorológica documentada y trazable** antes de la autorización del vuelo.
