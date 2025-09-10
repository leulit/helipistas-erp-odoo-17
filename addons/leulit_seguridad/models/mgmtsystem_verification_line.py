from odoo import fields, models, api


class MgmtsystemVerificationLine(models.Model):
    _name = "mgmtsystem.verification.line"
    _inherit = 'mgmtsystem.verification.line'


    def action_get_attachment_view(self):
        view_ref = self.env['ir.model.data'].get_object_reference('leulit_seguridad', 'leulit_20240722_1511_form')
        view_id = view_ref and view_ref[1] or False

        return {
           'type'           : 'ir.actions.act_window',
           'name'           : 'Añadir Documento',
           'res_model'      : 'mgmtsystem.verification.line',
           'view_mode'      : 'form',
           'view_id'        : view_id,
           'target'         : 'new',
           'res_id'         : self.id,
            'flags'         : {'form': {'action_buttons': True}}
        }
        return False
    

    def action_close(self):
        return {'type': 'ir.actions.act_window_close'}


    @api.depends('audit_id')
    def _compute_questions_audit(self):
        for item in self:
            list_questions = []
            for verification_line in item.audit_id.line_ids:
                list_questions.append(verification_line.question_id.id)
            item.questions_audit_ids = self.env['leulit.audit_question'].search([('id', 'in', list_questions)])


    question_id = fields.Many2one(comodel_name="leulit.audit_question", string="Pregunta", required=True, domain="[('estado','=','en_vigor')]")
    name = fields.Char(related='question_id.name', string="Question", required=True)
    notas = fields.Text(related='question_id.notas', string="Notas")
    norma = fields.Char(related='question_id.norma', string="Norma")
    conforme = fields.Selection([('si', 'Si'), ('no', 'No'), ('no_aplica', 'N/A')], string="Está conforme")
    procedure_id = fields.Many2one(related='question_id.procedure_id', comodel_name="leulit.procedure_audit_question", string="Procedimiento")
    procedimiento = fields.Char( string="Procedimiento")
    rel_docs = fields.One2many(comodel_name='ir.attachment', inverse_name='rel_verification_line', string='Documentos')
    questions_audit_ids = fields.One2many(comodel_name='leulit.audit_question', compute='_compute_questions_audit')

