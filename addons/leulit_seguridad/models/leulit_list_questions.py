from odoo import api, models, fields
from datetime import datetime, date, time


class LeulitListQuestions(models.Model):
    _name = "leulit.list_questions"
    _description = 'Lista de Preguntas'


    @api.onchange('question_id')
    def onchange_question(self):
        if self.question_id:
            self.notas = self.question_id.notas
            self.norma = self.question_id.norma
            self.procedimiento = self.question_id.procedimiento
        else:
            self.notas = ''
            self.norma = ''
            self.procedimiento = ''

    seq = fields.Integer(string="Secuencia")
    question_id = fields.Many2one(comodel_name="leulit.audit_question", string="Pregunta", required=True, domain="[('estado','=','en_vigor')]")
    notas = fields.Text(string="Notas")
    norma = fields.Char(string="Norma")
    procedimiento = fields.Char(string="Procedimiento")