"""Catálogos reutilizables para riesgos y controles PART-IS (SGSI)."""

from odoo import fields, models, _


class MageritThreat(models.Model):
    """Catálogo de amenazas estandarizadas para PART-IS."""

    _name = "mgmtsystem.risk.threat"
    _description = "PART-IS Threat"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    category = fields.Selection(
        selection=[
            ("natural", "Natural"),
            ("accidental", "Accidental"),
            ("deliberate", "Deliberada"),
            ("environmental", "Entorno"),
        ],
        string="Tipo de Amenaza",
        default="deliberate",
        help=_("Clasificación de la amenaza para priorizar mitigaciones."),
    )
    reference = fields.Char(
        string="Referencia",
        help=_("Código interno o referencia externa (ENS, ISO 27005, etc.)."),
    )
    description = fields.Text(translate=True)
    default_probability = fields.Selection(
        selection=[("1", "1"), ("2", "2"), ("3", "3"), ("4", "4"), ("5", "5")],
        string="Probabilidad Sugerida",
        help=_("Valor orientativo conforme al catálogo corporativo."),
    )
    active = fields.Boolean(default=True)


class MageritVulnerability(models.Model):
    """Catálogo de vulnerabilidades que afectan a activos en PART-IS."""

    _name = "mgmtsystem.risk.vulnerability"
    _description = "PART-IS Vulnerability"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    reference = fields.Char(
        string="Referencia",
        help=_("Código o identificador del catálogo corporativo."),
    )
    description = fields.Text(translate=True)
    mitigation = fields.Text(
        string="Mitigación Sugerida",
        translate=True,
        help=_("Acciones recomendadas para reducir la exposición."),
    )
    asset_ids = fields.Many2many(
        comodel_name="mgmtsystem.hazard",  # OCA base model para activos
        relation="mgmtsystem_vulnerability_asset_rel",
        column1="vulnerability_id",
        column2="asset_id",
        string="Activos Afectados",
        help=_("Activos donde se ha identificado la vulnerabilidad."),
    )
    active = fields.Boolean(default=True)


class PilarControl(models.Model):
    """Catálogo de controles asociados al tratamiento PART-IS (SGSI)."""

    _name = "mgmtsystem.risk.control"
    _description = "PART-IS Control"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    reference = fields.Char(
        string="Referencia",
        help=_("Identificador del control (ENS, ISO/IEC 27002, NIST, etc.)."),
    )
    control_type = fields.Selection(
        selection=[
            ("preventive", "Preventivo"),
            ("detective", "Detectivo"),
            ("corrective", "Correctivo"),
        ],
        string="Tipo",
        default="preventive",
        required=True,
    )
    objective = fields.Text(
        string="Objetivo",
        translate=True,
        help=_("Propósito funcional del control."),
    )
    implementation_hint = fields.Text(
        string="Guía de Implementación",
        translate=True,
        help=_("Notas para facilitar su despliegue dentro del SGSI."),
    )
    estimated_cost = fields.Float(
        string="Coste Estimado",
        help=_("Coste aproximado del control para análisis costo/beneficio."),
    )
    effectiveness_hint = fields.Text(
        string="Eficacia Esperada",
        translate=True,
        help=_("Escenario esperado tras implantar el control."),
    )
    active = fields.Boolean(default=True)
