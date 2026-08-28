# AI Coding Agent Instructions - Helipistas ERP Odoo 17

## Arquitectura del Proyecto

Este es un **ERP para gestión aeronáutica (helicópteros)** basado en Odoo 17, con módulos especializados para:
- **Operaciones**: Gestión de vuelos (`leulit_operaciones`), partes de vuelo, combustible
- **Mantenimiento**: Taller (`leulit_taller`), CAMO (`leulit_camo`), Parte 145 (`leulit_parte_145`)
- **Formación**: Escuela (`leulit_escuela`), alumnos, cursos, perfiles formativos
- **Calidad & Seguridad**: SMS, análisis de riesgo, auditorías
- **Almacén**: Control de inventario, calibraciones, lotes
- **Actividad**: Timesheet y facturación de horas de vuelo/taller

### Estructura de Módulos (Patrón Leulit)
```
addons/
  leulit/              # MÓDULO BASE - utilitylib compartida, grupos, widgets OWL
  leulit_*/            # Módulos funcionales (heredan de leulit)
  third-party-addons/  # Módulos de OCA y terceros
```

**CRÍTICO**: `leulit` es el módulo fundacional. Todos los módulos `leulit_*` dependen de él.

## Convenciones Específicas del Proyecto

### Biblioteca Compartida `utilitylib.py`
**Ubicación**: `addons/leulit/utilitylib.py`

Contiene constantes, funciones helper y configuración global:
```python
from odoo.addons.leulit import utilitylib

# Roles predefinidos
ROL_DIRECCION = 'Dirección'
ROL_PILOTO_EXTERNO = 'Piloto Externo'

# Formatos de fecha/hora
STD_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
ESP_DATE_FORMAT = "%d-%m-%Y"

# Densidades por modelo de helicóptero
DENSIDAD_COMBUSTIBLE = {'R44': 0.71, 'EC120B': 0.79, ...}
```

**Siempre importa utilitylib** en lugar de duplicar constantes:
```python
from odoo.addons.leulit import utilitylib
fecha_str = utilitylib.formatDate(fecha, utilitylib.ESP_DATE_FORMAT)
```

### Sistema de Grupos y Roles Jerárquicos
**Ubicación**: `addons/leulit/groups.xml`

Sistema de roles específico del dominio aeronáutico con herencia (`implied_ids`):
```xml
RBase → RBase_employee → RBase_hide
ROperaciones_piloto_externo → ROperaciones_alumno → ROperaciones_operador → ROperaciones_piloto → ROperaciones_responsable
```

**Patrón de Seguridad**:
- Define grupos en `groups.xml` (no en `security/`)
- Usa `security/ir.model.access.csv` para permisos CRUD por grupo
- Ejemplo: `access_analisis_riesgo_user,model_analisis_riesgo,group_riesgo_user,1,1,1,1`

### Widgets OWL Personalizados
**Ubicación**: `addons/leulit/static/src/js/widget_semaforo_field.js`

Widgets reutilizables registrados globalmente:
```javascript
// Uso en vistas XML
<field name="estado_caducidad" widget="semaforo_char"/>
<field name="es_valido" widget="semaforo_bool"/>
```

Muestra semáforos (verde/amarillo/rojo) para campos char/boolean. Registrados en `__manifest__.py`:
```python
'assets': {
    'web.assets_backend': [
        'leulit/static/src/js/widget_semaforo_field.js',
        'leulit/static/src/xml/semaforo_char.xml',
    ],
}
```

### Herencia de Vistas (XPath) - Patrón Dominante
**NUNCA copies vistas completas**. Siempre usa `inherit_id` + XPath:
```xml
<record id="view_partner_form_inherit" model="ir.ui.view">
    <field name="name">res.partner.form.inherit</field>
    <field name="model">res.partner</field>
    <field name="inherit_id" ref="base.view_partner_form"/>
    <field name="arch" type="xml">
        <xpath expr="//field[@name='vat']" position="after">
            <field name="licencia_piloto"/>
        </xpath>
    </field>
</record>
```

Ver ejemplos reales en: `addons/leulit_actividad/views/leulit_vuelo.xml`

### `readonly` en vistas: Odoo 17 NO guarda el valor

En Odoo 17 el cliente web **descarta** el valor de todo campo que esté `readonly`
en el momento de guardar. Si un `@api.onchange` rellena un campo y la vista lo
marca `readonly`, ese valor **no llega al servidor**: si el campo es `required`
revienta el `NOT NULL`, y si no lo es se pierde en silencio.

La combinación letal es un `readonly` que depende de un campo que el usuario
cambia en el mismo formulario:

```xml
<!-- MAL: al elegir el vuelo, el onchange rellena helicoptero_id y ese mismo
     acto lo vuelve readonly -> nunca se guarda -> NOT NULL violation -->
<field name="helicoptero_id" readonly="estado in [...] or vuelo_id"/>

<!-- BIEN: sigue bloqueado en pantalla, pero se envía -->
<field name="helicoptero_id" readonly="estado in [...] or vuelo_id" force_save="1"/>
```

Regla: **campo `readonly` que alguien escribe desde servidor u onchange →
`force_save="1"`**. Caso real: `leulit.anomalia` (commit c664b788).

### Gestión de Adjuntos (ir.attachment)
**Patrón crítico**: Override del método `check()` en `ir.attachment` para permitir acceso a adjuntos huérfanos (sin `res_model/res_id`) por usuarios `RBase`:
```python
# addons/leulit/models/ir_attachment.py
if not res_id and create_uid != self.env.uid:
    if not self.env.user.has_group('leulit.RBase'):
        raise AccessError(_("Perdon, you are not allowed..."))
```

**Al crear adjuntos programáticamente**, siempre establece `res_model` y `res_id`:
```python
attachment_id.write({
    'res_model': 'leulit.maintenance_manual',
    'res_id': record.id,
})
```

## Flujos de Trabajo Críticos

### Gestión de Vuelos (leulit_operaciones)
**Modelo principal**: `leulit.vuelo`
- Estados: `prevuelo → cerrado → cancelado`
- Validaciones: `checkValidCreateWriteData()` verifica solapamientos de helicóptero/piloto
- Perfiles dinámicos: `PV_PILOTO`, `PV_ALUMNO`, `PV_INSTRUCTOR`, `PV_VERIFICADO`
- Chain handlers: `vuelo_chain_postvuelo`, `vuelo_chain_cerrado` para lógica post-procesado

**Patrón de secuencias**:
```python
codigo = self.env['ir.sequence'].next_by_code('leulit.vuelo')
values.update({'codigo': codigo})
```

### Sistema de E-signature (leulit_esignature)
**TransientModel Wizard** para firmas digitales con QR + OTP:
```python
class EsignatureWizard(models.TransientModel):
    _name = "leulit_esignaturewizard"
    
    def prepareSignature(self, idmodelo, model, descripcion, referencia):
        otp = self.env['res.users'].get_otp()
        # Genera QR con pyqrcode
        qr = pyqrcode.create(qrtext)
```

Usado en anomalías, vuelos, partes de escuela para firma electrónica.

## Comandos de Desarrollo

### Docker (Desarrollo Local)
```bash
# Iniciar entorno
cd docker && docker-compose up -d

# Ver logs
docker logs -f helipistas_odoo_17

# Instalar dependencias Python en contenedor
docker exec -ti helipistas_odoo pip install pypdf pyqrcode pypng pyotp

# Acceso a shell Odoo
docker exec -ti helipistas_odoo /bin/bash
```

**Configuración**: `config/odoo.conf`
- `addons_path = /mnt/extra-addons,/mnt/extra-addons/third-party-addons`
- Puerto: `8070:8069` (http://localhost:8070)
- Base de datos: PostgreSQL 15 en contenedor `helipistas_psql_15`

### Actualización de Módulos
```bash
# Actualizar módulo específico
docker exec -ti helipistas_odoo odoo -u leulit_operaciones -d nombre_bd --stop-after-init

# Instalar nuevo módulo
docker exec -ti helipistas_odoo odoo -i leulit_nuevo_modulo -d nombre_bd --stop-after-init
```

### Migraciones y Mantenimiento
**CRÍTICO**: Antes de importar datos, ejecutar SQL del `README.md` para eliminar constraints problemáticos:
```sql
ALTER TABLE leulit_perfil_formacion DROP CONSTRAINT IF EXISTS leulit_perfil_formacion_alumno_perfil_unique;
ALTER TABLE maintenance_plan DROP CONSTRAINT IF EXISTS maintenance_plan_equipment_kind_uniq;
-- ... (ver README.md completo)
```

**Post-migración**: Requiere `res_company` con `id=2` para `leulit_almacen`.

## Patrones de Código Específicos

### Computed Fields con @api.depends
```python
@api.depends('partesescuela_teorico_ids')
def _compute_horas_teoricas(self):
    for rec in self:
        rec.horas_teoricas = sum(rec.partesescuela_teorico_ids.mapped('horas'))
```

**Evita `@api.depends()` vacíos** - especifica dependencias reales.

### Threading para Procesos Largos
Ver `addons/leulit/models/res_partner.py`:
```python
def _recalcular_complete_name_thread(self, dbname, uid):
    with api.Environment.manage():
        with registry(dbname).cursor() as new_cr:
            env = api.Environment(new_cr, uid, {})
            # ... proceso largo ...
            
def recalcular_complete_name_async(self):
    thread = threading.Thread(target=self._recalcular_complete_name_thread, args=(db, uid))
    thread.start()
```

### Logging Consistente
```python
import logging
_logger = logging.getLogger(__name__)

_logger.info('Iniciando recálculo de complete_name para %s partners', total)
_logger.error('Error al calcular complete_name para partner %s: %s', partner.id, str(e))
```

## Testing & Linting

- **Formato**: Black + isort para Python
- **Linting**: Pylint (configuración Odoo) + Flake8
- **Longitud línea**: 120 caracteres
- **Tests**: `tests/` usando `odoo.tests.common.TransactionCase`
- Ejecutar: `--test-enable --test-tags=tag_name`

## Referencias Rápidas

- **Módulos funcionales**: 16 módulos `leulit_*` + 1 base
- **Dependencias clave**: `pypdf`, `pyqrcode`, `pypng`, `pyotp`
- **Imagen Docker**: `wbms/odoo-17.0`
- **Formato fechas**: Siempre usar constantes de `utilitylib`
- **Multicompañía**: Considera `self.env.company` en lógica de negocio

---

## Principios Odoo 17+ (Heredados)

### Interaction Guidelines
User Persona: Asume que el usuario está familiarizado con los conceptos de programación y Python, pero puede ser nuevo en el framework de Odoo.

Explanations: Al generar código, proporciona explicaciones para las características específicas de Odoo, como el ORM, el entorno (self.env), los dominios, los decoradores @api, la herencia de vistas (XPath), el contexto y el framework OWL.

Clarification: Si una solicitud es ambigua, pide aclaraciones sobre la funcionalidad prevista y el impacto en los modelos o vistas existentes.

Dependencies: Al sugerir nuevos módulos de Odoo (en __manifest__.py) o bibliotecas externas de Python (en requirements.txt), explica sus beneficios y por qué son necesarios.

Formatting: Utiliza las herramientas Black y isort para garantizar un formato de código Python coherente. Utiliza el formateador XML integrado de tu editor para los archivos de vista.

Linting: Utiliza Pylint (con la configuración de Odoo) y Flake8 para detectar problemas comunes de Python y estilo. Fomenta el uso de pre-commit para automatizar esto.

Odoo Module Structure
Standard Structure: Asume una estructura de módulo estándar de Odoo:

__manifest__.py: Metadatos del módulo y dependencias.

__init__.py: Importa los subdirectorios (ej. from . import models).

models/: Contiene los modelos de Python (.py) y sus __init__.py.

views/: Contiene las definiciones de vistas, menús y acciones en XML.

controllers/: Contiene los controladores web de Python.

data/: Contiene archivos de datos XML (datos iniciales, noupdate="1").

security/: Contiene ir.model.access.csv y reglas de seguridad (ir.rule) en XML.

static/src/: Contiene activos web (JS/OWL, CSS/SASS, XML para plantillas OWL).

Odoo & Python Style Guide
PEP 8: Sigue estrictamente las directrices de PEP 8 para todo el código Python.

Odoo Conventions: Adhiérete a las Guías de Directrices de Odoo.

Naming:

Clases Python: PascalCase (ej. SaleOrder).

Modelos Odoo (_name): snake_case con puntos (ej. sale.order).

Variables/Funciones: snake_case (ej. compute_total_amount).

Campos de Modelo: snake_case (ej. partner_id, amount_total).

Line Length: Apunta a 120 caracteres como máximo (común en la comunidad de Odoo).

Translatability: Todas las cadenas de texto orientadas al usuario (etiquetas, mensajes) deben estar envueltas en _() para la traducción.

Python

from odoo import _
...
raise UserError(_("This is a translatable error message."))
Logging: Usa el logger estándar de Python, no print().

Python

import logging
_logger = logging.getLogger(__name__)
_logger.info("This is an informational message.")
Core Odoo Concepts
ORM (Object-Relational Mapping)
Evitar SQL Crudo: Prefiere siempre los métodos del ORM (search, browse, create, write) sobre self.env.cr.execute(). El ORM maneja la seguridad y es más mantenible.

SQL Seguro: Si el SQL crudo es absolutamente necesario, nunca uses formato de cadenas (ej. f-strings) para construir consultas. Usa placeholders para prevenir la inyección de SQL.

Python

# MAL: Riesgo de inyección SQL
self.env.cr.execute(f"SELECT id FROM res_partner WHERE name = '{name}'")

# BIEN: Parametrizado
self.env.cr.execute("SELECT id FROM res_partner WHERE name = %s", (name,))
Rendimiento:

Evita bucles que llamen a write(), create() o unlink(). Realiza operaciones por lotes.

No llames al ORM (especialmente search o write) dentro de un bucle for sobre un recordset.

Usa search_read(), read_group(), y especifica los campos (fields=[...]) para obtener solo los datos que necesitas.

Entorno (self.env):

Usa self.env para acceder al entorno y otros modelos.

Usa self.env.user para obtener el usuario actual y self.env.company para la compañía actual.

Usa self.with_context(...) o self.with_company(...) para modificar el entorno para una llamada específica.

Model Decorators
@api.depends: Úsalo para métodos de cómputo (compute=) y onchange. Sé específico en las dependencias para evitar recálculos innecesarios.

@api.constrains: Úsalo para validaciones a nivel de base de datos.

@api.onchange: Úsalo para la lógica de UI dinámica en formularios.

@api.model / @api.model_create_multi: Úsalo para métodos que no operan en un self de registro (ej. create()).

🧬 Software Architecture & Principles
SOLID Principles in Odoo
Aplica los principios SOLID para un código limpio y mantenible.

(S) Single Responsibility Principle: Un modelo o método debe tener una única razón para cambiar.

En Odoo: Evita los "modelos dios". Si tu modelo sale.order también gestiona lógica de fabricación compleja, considera mover esa lógica a su propio modelo (mrp.production.request) y simplemente vincularlos.

(O) Open/Closed Principle: El software debe estar abierto a la extensión, pero cerrado a la modificación.

En Odoo: Este es el núcleo de Odoo. Usa _inherit para extender modelos y vistas sin modificar el código original del módulo base o sale.

(L) Liskov Substitution Principle: Los subtipos deben ser sustituibles por sus tipos base.

En Odoo: Si heredas y sobrescribes un método (ej. action_confirm de sale.order), tu nueva implementación debe cumplir el contrato original. Debe devolver lo que se espera y no romper el flujo de negocio que depende de él.

(I) Interface Segregation Principle: No se debe obligar a un cliente a depender de métodos que no utiliza.

En Odoo: Evita heredar de modelos (_inherit) solo para usar uno o dos campos. Prefiere usar Many2one o self.env['other.model'] para acceder a la información que necesitas. Crea clases models.AbstractModel (mixins) limpias si necesitas compartir un conjunto coherente de funcionalidades.

(D) Dependency Inversion Principle: Los módulos de alto nivel no deben depender de los de bajo nivel; ambos deben depender de abstracciones.

En Odoo: Utiliza el ORM (self.env[...]) como la abstracción. Tu lógica de negocio (alto nivel) no debe depender de una implementación SQL específica (bajo nivel), sino del modelo (product.product) y sus métodos (search, read).

Performance & Optimization
ORM in Loops (¡Prohibido!): Nunca llames a search(), create(), write(), o browse() dentro de un bucle for. Pre-carga todos los datos de una vez.

Python

# MAL: Llama a la BBDD en cada iteración
for order in orders:
    partner_name = self.env['res.partner'].browse(order.partner_id.id).name

# BIEN: El prefetching de Odoo (browse) maneja esto
for order in orders:
    partner_name = order.partner_id.name # No hay llamadas extra

# MAL: Búsqueda en un bucle
for data in my_data_list:
    product = self.env['product.product'].search([('default_code', '=', data['code'])])

# BIEN: Búsqueda por lotes
all_codes = [data['code'] for data in my_data_list]
products = self.env['product.product'].search([('default_code', 'in', all_codes)])
search_read y read_group: Para lecturas de datos, prefiere search_read() (para obtener datos como diccionarios) o read_group() (para agregaciones) sobre search() seguido de un bucle. Es mucho más rápido.

Campos Computados: Los campos computados son potentes pero caros.

No les añadas store=True a menos que sea absolutamente necesario (ej. para búsquedas o agrupaciones).

Sé muy preciso con tus dependencias @api.depends().

SQL Crudo (Solo Lectura): Para informes complejos que son imposibles con el ORM, usa self.env.cr.execute() para leer datos. Nunca lo uses para escribir datos, ya que anula el ORM y la lógica de negocio.

Scalability & Fault Tolerance
Tareas Asíncronas (Jobs): No bloquees la interfaz de usuario. Para cualquier operación que tarde más de unos segundos (enviar correos electrónicos, procesar archivos, sincronizaciones API), usa un job asíncrono.

En Odoo: Usa el módulo queue_job. Decora tu método con @job y llámalo con .delay().

Python

from odoo.addons.queue_job.exception import RetryableJobError
from odoo import api, models

class MyModel(models.Model):
    _inherit = 'my.model'

    def _my_long_process(self):
        # ... lógica larga ...
        if api_call.failed():
            raise RetryableJobError("API falló, reintentar más tarde")

    def start_long_process(self):
        self.delayable(identity_key="mi_proceso_unico")._my_long_process()
Tolerancia a Fallos:

Transacciones: Odoo envuelve la mayoría de las operaciones en una transacción. Si falla, se revierte.

Jobs Reintentables: Usa RetryableJobError (de queue_job) para permitir que una tarea fallida se reintente automáticamente.

Idempotencia: Diseña tus jobs y controladores de webhook para que sean idempotentes (puedan ejecutarse varias veces con el mismo resultado) para evitar datos duplicados si una transacción falla y se reintenta.

Odoo Best Practices
Herencia (_inherit):

Extender un Modelo: Usa _inherit = 'model.name' para agregar campos o métodos a un modelo existente.

Nuevo Modelo (Delegation): Usa _inherit = 'model.name' y _inherits = {'other.model': 'field_id'} para la herencia por delegación.

Seguridad:

Access Rights: Define siempre los permisos en security/ir.model.access.csv.

Record Rules: Usa security/your_rules.xml para definir reglas de seguridad a nivel de registro (ej. multi-compañía, solo ver registros propios).

Grupos: Define nuevos grupos de seguridad en XML si es necesario.

Datos (data/):

Usa archivos de datos XML para cargar configuraciones, plantillas, etc.

Usa noupdate="1" para datos que el usuario pueda modificar después de la instalación (para evitar sobrescribirlos en las actualizaciones).

Wizards (TransientModel): Usa models.TransientModel para asistentes (popups) que guían al usuario a través de un proceso. Los datos del asistente son temporales.

Odoo Controllers (Web Layer)
Rutas: Usa el decorador @http.route() para definir nuevas rutas web.

Autenticación: Especifica auth='user' (requiere inicio de sesión), auth='public' (abierto a todos) o auth='none'.

JSON vs HTTP: Usa type='json' para endpoints de API (consumidos por JS/OWL) y type='http' para páginas web (renderizadas con QWeb).

Python

from odoo import http

class MyController(http.Controller):
    @http.route('/my_page', auth='public', website=True)
    def my_page(self, **kw):
        return http.request.render('my_module.my_template_page')
🎨 Frontend & UI Development (Vistas, Widgets & OWL)
La creación de una interfaz de usuario (UI) intuitiva y el desarrollo de widgets personalizados son fundamentales para una buena experiencia de usuario en Odoo. Esto se logra a través de dos componentes principales: las Vistas XML (la estructura) y el framework OWL (la interactividad).

Vistas (XML)
Herencia de Vistas: Nunca copies y pegues una vista completa para modificarla. Siempre usa <xpath expr="..."> para heredar y modificar vistas existentes. Esto es crucial para la mantenibilidad y la compatibilidad con otros módulos.

XML

<record id="view_partner_form_inherit" model="ir.ui.view">
    <field name="name">res.partner.form.inherit</field>
    <field name="model">res.partner</field>
    <field name="inherit_id" ref="base.view_partner_form"/>
    <field name="arch" type="xml">
        <xpath expr="//field[@name='vat']" position="after">
            <field name="my_new_field"/>
        </xpath>
    </field>
</record>
Vistas Semánticas: Usa las etiquetas de Odoo (<group>, <notebook>, <page>, <field>) correctamente para construir formularios y listas claras.

Contexto y Dominio: Usa context="{...}" y domain="[...]" en acciones y campos para filtrar vistas, establecer valores predeterminados o pasar información.

Widgets de Vista: Usa el atributo widget="widget_name" en los campos XML para aplicar widgets existentes (ej. widget="many2many_tags", widget="monetary").

Odoo Web Library (OWL)
Odoo 17+ usa OWL (Odoo Web Library) como su framework de frontend principal.

Framework Esencial: OWL es la herramienta para construir cualquier interactividad del lado del cliente, desde un simple widget hasta vistas completas.

Componentes: La UI se construye a base de Componentes OWL (similares a React o Vue).

Desarrollo de Widgets: El desarrollo de widgets de campo personalizados (ej. un selector de color, un campo de firma, un char con formato especial) se realiza creando nuevos Componentes OWL y registrándolos en el framework de vistas para que puedan ser usados en el XML (ej. widget="mi_widget_personalizado").

Hooks: Usa hooks de OWL (ej. useState, onWillStart, useRef) para gestionar el estado, el ciclo de vida y las referencias a elementos.

Servicios y RPC: Usa los servicios de Odoo (como rpc, notification, action) para interactuar con el backend (llamar a métodos de Python) y el framework de Odoo.

Ubicación: Todo el código JS/OWL, SASS/CSS e imágenes se encuentra en el directorio static/src/... del módulo.

Error Handling & Logging
UserError: Lanza una UserError para errores funcionales o validaciones que el usuario final deba entender. Esto se muestra en un diálogo limpio.

Python

from odoo.exceptions import UserError

if not partner.email:
    raise UserError(_("The partner must have an email address."))
ValidationError: Lanza una ValidationError dentro de un método @api.constrains para mostrar un error de validación.

Otras Excepciones: Para errores técnicos, lanza excepciones estándar de Python. Estos serán registrados y mostrarán un mensaje de error genérico al usuario.

Testing
Tests de Python: Escribe tests unitarios y de integración usando el framework de Odoo (odoo.tests.common.TransactionCase o HttpCase).

Ubicación: Coloca los tests en un directorio tests/.

Ejecución: Ejecuta tests usando --test-enable o --test-tags al iniciar Odoo.

Pruebas de UI: Usa los tests de Tour de Odoo (basados en JavaScript) para probar flujos de usuario en el frontend.

Documentation
Docstrings: Escribe docstrings estilo Google o reStructuredText para todas las clases y métodos públicos.

README: Incluye un README.md o README.rst en tu módulo explicando qué hace, cómo configurarlo y quién lo mantiene.

Comentarios: Usa # para comentarios en línea que expliquen el por qué de un código complejo, no el qué.