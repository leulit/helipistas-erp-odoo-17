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
