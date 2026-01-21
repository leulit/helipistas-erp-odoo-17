from odoo import fields, models, tools, api


class leulit_report_pf_curso(models.Model):
    _name = "leulit.report_pf_curso"
    _auto = False
    _description = "Perfil Formación Curso Report"


    def open_cursos_perfil_formacion(self):
        pf_cursos = self.env['leulit.perfil_formacion_curso'].search([('curso','=',self.curso.id),('alumno','=',self.alumno.id)])
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('leulit_escuela.leulit_20201106_1607_tree')
        view_id = view_ref and view_ref[1] or False
        return {
            'type'           : 'ir.actions.act_window',
            'name'           : 'Curso Perfil Formación',
            'res_model'      : 'leulit.perfil_formacion_curso',
            'view_mode'      : 'tree',
            'view_id'        : view_id,
            'domain'         : [('id', 'in', pf_cursos.ids)],
            }


    curso = fields.Many2one(comodel_name="leulit.curso",string="Curso")
    pf_curso = fields.Many2one(comodel_name="leulit.perfil_formacion_curso",string="Perfil formación curso")
    alumno = fields.Many2one(comodel_name="leulit.alumno",string="Alumno")
    
    last_done_date = fields.Date(related='pf_curso.last_done_date',string='Done date')
    next_done_date = fields.Date(related='pf_curso.next_done_date',string='Next done date')
    remainder_dy = fields.Integer(related='pf_curso.remainder_dy',string='Remain. (DY)')
    semaforo_dy = fields.Char(related='pf_curso.semaforo_dy',string='Semáforo')


    def init(self):
        tools.drop_view_if_exists(self._cr, "leulit_report_pf_curso")
        self.env.cr.execute("""
            CREATE or REPLACE VIEW {} as (
                SELECT
                    row_number() OVER () AS id,
                    max(leulit_perfil_formacion_curso.id) as pf_curso,
                    leulit_perfil_formacion_curso.alumno,
					curso
                FROM leulit_perfil_formacion_curso
								JOIN leulit_perfil_formacion
								ON leulit_perfil_formacion_curso.perfil_formacion = leulit_perfil_formacion.id
                WHERE leulit_perfil_formacion.inactivo = 'f' and finalizado = 'f' and leulit_perfil_formacion_curso.alumno is not null
				GROUP BY leulit_perfil_formacion_curso.alumno, curso
            )""".format(self._table)
        )
