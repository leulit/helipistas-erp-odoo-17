"""Inventario de equipos IT para cumplimiento SGSI PART-IS/AESA."""

from datetime import date

from odoo import api, fields, models


DEVICE_TYPE = [
    ("desktop", "Ordenador de sobremesa"),
    ("laptop", "Portátil"),
    ("tablet", "Tablet"),
    ("smartphone", "Teléfono móvil"),
    ("server", "Servidor"),
    ("network", "Equipo de red"),
    ("peripheral", "Periférico"),
    ("other", "Otro"),
]

EQUIPMENT_STATE = [
    ("in_service", "En servicio"),
    ("stock", "En almacén"),
    ("repair", "En reparación"),
    ("retired", "Retirado"),
]

PATCH_STATUS = [
    ("updated", "Actualizado"),
    ("pending", "Actualización pendiente"),
    ("unsupported", "Sin soporte del fabricante"),
]


class LeulitPartisEquipment(models.Model):
    """Equipo IT del inventario del SGSI PART-IS (ordenadores, tablets, móviles...)."""

    _name = "leulit.partis.equipment"
    _description = "Equipo IT - Inventario SGSI PART-IS"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "inventory_code, name"

    name = fields.Char(string="Nombre / Descripción", required=True, tracking=True)
    inventory_code = fields.Char(
        string="Código de inventario", required=True, copy=False, index=True,
        tracking=True,
        help="Identificador único del equipo en el inventario del SGSI.")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company", string="Compañía",
        default=lambda self: self.env.company)

    device_type = fields.Selection(
        selection=DEVICE_TYPE, string="Tipo de equipo",
        required=True, default="laptop", tracking=True)
    manufacturer = fields.Char(string="Fabricante")
    model_name = fields.Char(string="Modelo")
    serial_number = fields.Char(string="Número de serie", tracking=True)

    assigned_user_id = fields.Many2one(
        "hr.employee", string="Usuario asignado", tracking=True)
    department_id = fields.Many2one("hr.department", string="Departamento")
    location = fields.Char(string="Ubicación física")

    purchase_date = fields.Date(string="Fecha de compra")
    warranty_end_date = fields.Date(string="Fin de garantía")
    warranty_active = fields.Boolean(
        string="En garantía", compute="_compute_warranty_active", store=True)

    state = fields.Selection(
        selection=EQUIPMENT_STATE, string="Estado",
        required=True, default="in_service", tracking=True)

    encryption_enabled = fields.Boolean(
        string="Cifrado de disco", tracking=True,
        help="El almacenamiento del equipo está cifrado (control SGSI).")
    antivirus_enabled = fields.Boolean(
        string="Antivirus / EDR", tracking=True,
        help="El equipo dispone de protección antivirus o EDR activa.")
    patch_status = fields.Selection(
        selection=PATCH_STATUS, string="Estado de parcheo",
        default="updated", tracking=True)

    asset_id = fields.Many2one(
        "mgmtsystem.hazard", string="Activo de información SGSI",
        help="Activo de información PART-IS asociado a este equipo.")

    notes = fields.Html(string="Notas")

    _sql_constraints = [
        ("inventory_code_uniq", "unique(inventory_code, company_id)",
         "El código de inventario debe ser único por compañía."),
    ]

    @api.depends("warranty_end_date")
    def _compute_warranty_active(self):
        today = date.today()
        for equipment in self:
            equipment.warranty_active = bool(
                equipment.warranty_end_date
                and equipment.warranty_end_date >= today)

    @api.depends("name", "inventory_code")
    def _compute_display_name(self):
        for equipment in self:
            if equipment.inventory_code:
                equipment.display_name = "[%s] %s" % (
                    equipment.inventory_code, equipment.name or "")
            else:
                equipment.display_name = equipment.name or ""
