# Integración METAR/TAF con el Parte de Vuelo (`leulit_vuelo`)

Este documento muestra cómo vincular la consulta meteorológica automática al parte de vuelo del módulo `leulit_vuelo`. El objetivo es que cada parte de vuelo quede enlazado con el METAR/TAF vigente en el momento de su autorización, a efectos operacionales y de trazabilidad AESA.

---

## 1. Modelo — añadir el campo METAR al parte de vuelo

La integración usa `briefing_oaci` como único punto de entrada (ver sección 1.1).
`briefing_oaci` devuelve `record_id=None`; los datos se almacenan directamente como campos de texto en el parte.

```python
# addons/leulit_vuelo/models/leulit_vuelo.py

from odoo import _, fields, models
from odoo.exceptions import UserError


class LeulitVuelo(models.Model):
    _inherit = 'leulit.vuelo'

    meteo_raw_metar = fields.Text(string='METAR', readonly=True)
    meteo_raw_taf = fields.Text(string='TAF', readonly=True)
    meteo_observation_time = fields.Datetime(string='Hora observación (UTC)', readonly=True)
    meteo_icao = fields.Char(string='OACI meteorología', readonly=True)

    def action_obtener_meteo_salida(self):
        """Obtiene el briefing meteorológico del aeródromo de salida y lo almacena."""
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

            vuelo.write({
                'meteo_raw_metar': result['raw_metar'],
                'meteo_raw_taf': result['raw_taf'],
                'meteo_observation_time': result['observation_time'],
                'meteo_icao': result['metar_icao'],
            })

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

---

## 1.1 API: `briefing_oaci`

`briefing_oaci` es el punto de entrada para obtener el briefing de un OACI desde cualquier módulo. Devuelve METAR oficial, TAF oficial y el registro vinculado.

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
    'record_id':        42,             # id del registro leulit.meteo.metar
    'raw_metar':        'LEBL ...',     # pestaña METAR del formulario
    'raw_taf':          'TAF LEBL ...', # pestaña TAF del formulario
    'historico':        False,          # True si los datos vienen de BD sin actualizar
    'observation_time': datetime(...),  # hora UTC de la observación
    'provider':         'aemet',        # proveedor usado ('aemet', 'checkwx', ...)
    'metar_icao':       'LEBL',         # OACI del que procede el METAR/TAF
                                        # (puede diferir del icao_code solicitado
                                        #  si el OACI pedido no tiene METAR propio)
    'usa_referencia':   True,           # True si metar_icao ≠ icao_code solicitado
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

> `briefing_oaci` lee siempre de `leulit.meteo.historico`. Ese modelo lo alimenta el cron
> (`action_actualizar_metar_cron`) cada ~30 min. Sin cron activo no hay datos históricos.

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
<page string="Meteorología" name="page_meteo"
      attrs="{'invisible': [('meteo_raw_metar', '=', False)]}">
    <group string="METAR / TAF de salida">
        <field name="meteo_icao" string="OACI" readonly="1"/>
        <field name="meteo_observation_time" string="Hora observación (UTC)" readonly="1"/>
    </group>
    <group string="Textos oficiales">
        <field name="meteo_raw_metar" string="METAR" readonly="1" widget="text"/>
        <field name="meteo_raw_taf" string="TAF" readonly="1" widget="text"/>
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

Los campos `meteo_*` son columnas del propio modelo `leulit.vuelo`, por lo que no se necesita acceso adicional a modelos de `leulit_meteo`. Solo hay que asegurarse de que el perfil de piloto/operaciones tiene permiso de escritura sobre `leulit.vuelo` para que el botón pueda guardar los datos.

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
| `meteo_icao` | `LEUL` | OACI del que procede el briefing |
| `meteo_raw_metar` | `LEUL 271430Z 12009KT CAVOK 23/12 Q1017` | Texto METAR oficial sin alterar |
| `meteo_raw_taf` | `TAF LEUL …` | Texto TAF oficial sin alterar |
| `meteo_observation_time` | 27/04/2026 14:30 UTC | Hora de la observación METAR |

Esto permite demostrar ante AESA que **existió una consulta meteorológica documentada y trazable** antes de la autorización del vuelo.
