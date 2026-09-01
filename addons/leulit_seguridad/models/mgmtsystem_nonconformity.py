from odoo import _, api, fields, models, registry
from odoo.exceptions import ValidationError
import logging
import threading

_logger = logging.getLogger(__name__)

# Icarus Manteniment = compañía 2, sin xmlid en la BD (mismo criterio que
# leulit_almacen/data/leulit_estanterias.xml: se referencia por id).
ICARUS_COMPANY_ID = 2
SISTEMA_PARTE_145 = "Parte 145"


class MgmtsystemNonconformity(models.Model):
    _inherit = "mgmtsystem.nonconformity"

    motivo_cierre = fields.Text(string="Motivo de Cierre")

    nc_relacionada_id = fields.Many2one(
        "mgmtsystem.nonconformity",
        string="NC relacionada (otra empresa)",
        copy=False,
        readonly=True,
        help="Copia automática de esta NC en la otra empresa, o la NC original de la que "
             "esta es copia. Se genera cuando una NC se crea en Helipistas con el sistema "
             "'Parte 145': Icarus Manteniment, como organización de mantenimiento aprobada "
             "Part-145, necesita su propio registro para su sistema de calidad aunque el "
             "hallazgo se haya originado en Helipistas.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._crear_espejo_nc_icarus_parte_145()
        return records

    def _crear_espejo_nc_icarus_parte_145(self):
        """Solo se rellenan nombre y descripción (con una nota indicando de qué NC de
        Helipistas proviene): el resto de campos (responsable, sistema, orígenes...) los
        completa el encargado de seguridad de Icarus al triarla, no tienen por qué coincidir
        con los de Helipistas."""
        icarus = self.env["res.company"].sudo().browse(ICARUS_COMPANY_ID).exists()
        if not icarus:
            _logger.warning(
                "No existe la compañía Icarus Manteniment (id=%s): no se crea la NC espejo.",
                ICARUS_COMPANY_ID,
            )
            return
        helipistas = self.env.ref("base.main_company")
        for nc in self:
            if nc.company_id != helipistas or nc.nc_relacionada_id:
                continue
            if not nc.system_id or (nc.system_id.name or "").strip() != SISTEMA_PARTE_145:
                continue
            nota = _('Copia automática de la NC "%s" de Helipistas.') % nc.ref
            descripcion = "%s\n\n%s" % (nota, nc.description or "")
            espejo = self.env["mgmtsystem.nonconformity"].sudo().create({
                "name": nc.name,
                "description": descripcion,
                "company_id": icarus.id,
                "nc_relacionada_id": nc.id,
            })
            nc.sudo().write({"nc_relacionada_id": espejo.id})

    @api.constrains("stage_id")
    def _check_close_with_evaluation(self):
        # El cierre rápido solo se activa cuando el write viene del wizard
        # "Cerrar NC" (que marca este contexto): usar la presencia de
        # motivo_cierre como señal era incorrecto, porque ese campo persiste
        # en el registro y una vez relleno activaba el atajo también al
        # cerrar la NC del modo normal, clicando el estado directamente.
        cierre_rapido = self.filtered(
            lambda nc: nc.state == "done" and self.env.context.get("cierre_rapido_nc")
        )
        for nc in cierre_rapido:
            if not nc.immediate_action_id:
                raise ValidationError(
                    _("La Acción Inmediata es obligatoria para cerrar la No Conformidad "
                      "con el botón 'Cerrar NC'.")
                )

        # Para el resto (flujo normal de estados), se mantiene la validación original
        resto = self - cierre_rapido
        if resto:
            super(MgmtsystemNonconformity, resto)._check_close_with_evaluation()

    def action_abrir_wizard_cerrar(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Cerrar No Conformidad"),
            "res_model": "leulit.wizard.cerrar.nc",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_nc_id": self.id,
                "default_immediate_action_id": self.immediate_action_id.id or False,
            },
        }

    @api.depends("description")
    def _compute_short_description(self):
        for record in self:
            record.short_description = record.description[:100] if record.description else ""

    short_description = fields.Char(
        "Description",
        compute="_compute_short_description",
        store=True,
        readonly=True,
    )
    partner_id = fields.Many2one("res.partner", "Partner", required=False)
    create_date = fields.Datetime("Creado en", readonly=False)
    responsible_user_id = fields.Many2one(
        "res.users", "Responsible", required=False, tracking=True
    )
    manager_user_id = fields.Many2one(
        "res.users", "Manager", required=False, tracking=True
    )
    origin_ids = fields.Many2many(
        "mgmtsystem.nonconformity.origin",
        "mgmtsystem_nonconformity_origin_rel",
        "nonconformity_id",
        "origin_id",
        "Origin",
        required=False,
    )
    risk_type_id = fields.Many2one("mgmtsystem.hazard.risk.type", string="Peligro")

    # Al cerrar/cancelar una NC (sea desde el wizard "Cerrar NC" o haciendo
    # clic directamente en la barra de estados), sus acciones asociadas
    # (action_ids + immediate_action_id) se sincronizan al estado que
    # corresponda, para que no se queden abiertas si el responsable de
    # seguridad no las repasa una a una. El paso a "En progreso" ya lo hace
    # el módulo base (mgmtsystem_nonconformity.write()) abriendo las
    # acciones en borrador.
    _ACTION_STAGE_XMLID_POR_ESTADO_NC = {
        "done": "mgmtsystem_action.stage_close",
        "cancel": "mgmtsystem_action.stage_cancel",
    }

    def write(self, vals):
        create_date = vals.pop("create_date", None)
        cambia_stage = "stage_id" in vals
        estados_previos = {nc.id: nc.state for nc in self} if cambia_stage else {}
        res = super().write(vals)
        if create_date:
            self._cr.execute(
                "UPDATE mgmtsystem_nonconformity SET create_date = %s WHERE id IN %s",
                (create_date, tuple(self.ids)),
            )
            self.invalidate_recordset(["create_date"])
        if cambia_stage:
            for nc in self:
                if nc.state != estados_previos.get(nc.id):
                    nc._sincronizar_estado_acciones()
        return res

    def _sincronizar_estado_acciones(self):
        self.ensure_one()
        xmlid = self._ACTION_STAGE_XMLID_POR_ESTADO_NC.get(self.state)
        if not xmlid:
            return
        stage = self.env.ref(xmlid, raise_if_not_found=False)
        if not stage:
            return
        acciones = self._get_all_actions().filtered(lambda a: not a.stage_id.is_ending)
        if acciones:
            acciones.write({"stage_id": stage.id})

    def set_default_origin_on_nonconformity(self):
        _logger.error("################### set_default_origin_on_nonconformity")
        threaded_calculation = threading.Thread(target=self.run_set_default_origin_on_nonconformity)
        _logger.error("################### set_default_origin_on_nonconformity start thread")
        threaded_calculation.start()

    def run_set_default_origin_on_nonconformity(self):
        db_registry = registry(self.env.cr.dbname)
        with db_registry.cursor() as new_cr:
            env = api.Environment(new_cr, self.env.uid, self.env.context)
            origin = env['mgmtsystem.nonconformity.origin'].sudo().browse(24)
            nonconformities = env['mgmtsystem.nonconformity'].sudo().search([
                ('origin_ids', '=', False)
            ])
            for nc in nonconformities:
                nc.write({'origin_ids': [(4, origin.id)]})
                new_cr.commit()
        _logger.error('################### set_default_origin_on_nonconformity fin thread')