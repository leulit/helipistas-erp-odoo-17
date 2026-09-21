# -*- encoding: utf-8 -*-
from collections import defaultdict
from datetime import datetime, time, timedelta

from odoo import api, fields, models

USER_EMILIO = 11
USER_PAU = 14

PERSONA_EMILIO = 'Emilio Álvarez'
PERSONA_PAU = 'Pau Barbarroja'
PERSONA_AMBOS = 'Ambos'
PERSONAS = (PERSONA_EMILIO, PERSONA_PAU, PERSONA_AMBOS)

SEMANAS = 12

# Nombre de etapa (casefold) -> columna. Cualquier otro nombre (p. ej. "N/A") se ignora.
# Los nombres "hechos" coinciden con onchange_stage_id (models/project_task.py).
ETAPA_A_COLUMNA = {
    'pendiente': 'pendiente',
    'en proceso': 'en_proceso',
    'pospuesta': 'pospuesta',
    'realizada': 'realizada',
    'hecho': 'realizada',
    'finalizado': 'realizada',
}


class TareaSemanaEstado(models.TransientModel):
    _name = 'leulit.tarea.semana.estado'
    _description = 'Tareas por semana y estado'
    _order = 'semana_inicio desc, persona'

    semana_inicio = fields.Date(string='Inicio de semana')
    semana = fields.Char(string='Semana')
    persona = fields.Char(string='Persona')
    pendiente = fields.Integer(string='Pendiente')
    en_proceso = fields.Integer(string='En proceso')
    pospuesta = fields.Integer(string='Pospuesta')
    realizada = fields.Integer(string='Realizada')
    # Ids de las tareas de cada celda ({columna: [ids]}); un m2m almacenado perdía filas al crear
    tareas_json = fields.Json()
    pendiente_ids = fields.Many2many('project.task', compute='_compute_tareas', string='Pendiente')
    en_proceso_ids = fields.Many2many('project.task', compute='_compute_tareas', string='En proceso')
    pospuesta_ids = fields.Many2many('project.task', compute='_compute_tareas', string='Pospuesta')
    realizada_ids = fields.Many2many('project.task', compute='_compute_tareas', string='Realizada')

    @api.depends('tareas_json')
    def _compute_tareas(self):
        tareas = self.env['project.task'].with_context(active_test=False)
        for rec in self:
            datos = rec.tareas_json or {}
            for col in set(ETAPA_A_COLUMNA.values()):
                rec[col + '_ids'] = tareas.browse(datos.get(col, [])).exists()

    @api.model
    def abrir_tabla(self, hoy=None):
        """Regenera las filas del usuario y devuelve la acción con la tabla."""
        self.search([('create_uid', '=', self.env.uid)]).unlink()
        self.create(self._calcular_filas(hoy))
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tareas por semana y estado',
            'res_model': self._name,
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('leulit_tarea.leulit_20260921_1100_tree').id, 'tree'),
                (self.env.ref('leulit_tarea.leulit_20260921_1102_form').id, 'form'),
            ],
            'domain': [('create_uid', '=', self.env.uid)],
            'context': {'group_by': ['semana_inicio:week']},
            'target': 'current',
            'help': (
                '<p>Pendiente, En proceso y Pospuesta: foto de las tareas al cierre de la semana '
                '(la semana en curso, hasta hoy).</p>'
                '<p>Realizada: tareas cerradas durante esa semana que siguen cerradas al cierre de la misma.</p>'
            ),
        }

    @api.model
    def _calcular_filas(self, hoy=None):
        hoy = hoy or fields.Datetime.now()
        lunes_actual = hoy.date() - timedelta(days=hoy.weekday())
        semanas = []
        for i in range(SEMANAS):
            inicio = lunes_actual - timedelta(weeks=i)
            es_actual = i == 0
            corte = hoy if es_actual else datetime.combine(inicio + timedelta(days=6), time(23, 59, 59))
            semanas.append((inicio, datetime.combine(inicio, time.min), corte, es_actual))

        contadores = {
            (inicio, persona): {col: [] for col in set(ETAPA_A_COLUMNA.values())}
            for inicio, _ini, _corte, _act in semanas
            for persona in PERSONAS
        }

        tareas = self.env['project.task'].with_context(active_test=False).search(
            [('user_ids', 'in', [USER_EMILIO, USER_PAU]), ('create_date', '<=', hoy)]
        ).filtered(lambda t: not t.project_borrador)

        if tareas:
            campo_etapa = self.env['ir.model.fields']._get('project.task', 'stage_id')
            trackings = self.env['mail.tracking.value'].sudo().search(
                [
                    ('field_id', '=', campo_etapa.id),
                    ('mail_message_id.model', '=', 'project.task'),
                    ('mail_message_id.res_id', 'in', tareas.ids),
                ],
                order='create_date, id',
            )
            por_tarea = defaultdict(list)
            for tr in trackings:
                por_tarea[tr.mail_message_id.res_id].append(tr)

            etapas = self.env['project.task.type'].with_context(active_test=False).search([])
            columna_de_etapa = {e.id: ETAPA_A_COLUMNA.get((e.name or '').casefold()) for e in etapas}

            for tarea in tareas:
                ids = set(tarea.user_ids.ids)
                if USER_EMILIO in ids and USER_PAU in ids:
                    persona = PERSONA_AMBOS
                elif USER_EMILIO in ids:
                    persona = PERSONA_EMILIO
                else:
                    persona = PERSONA_PAU
                trs = por_tarea.get(tarea.id, [])
                for inicio, dt_inicio, corte, _act in semanas:
                    if tarea.create_date > corte:
                        continue
                    etapa_id, desde = self._etapa_a_fecha(tarea, trs, corte)
                    columna = columna_de_etapa.get(etapa_id)
                    if not columna:
                        continue
                    if columna == 'realizada' and desde < dt_inicio:
                        continue
                    contadores[(inicio, persona)][columna].append(tarea.id)

        filas = []
        for inicio, _ini, _corte, es_actual in semanas:
            fin = inicio + timedelta(days=6)
            etiqueta = 'S%02d %s (%s - %s)' % (
                inicio.isocalendar()[1], inicio.isocalendar()[0],
                inicio.strftime('%d/%m'), fin.strftime('%d/%m'),
            )
            if es_actual:
                etiqueta += ' · hasta hoy'
            for persona in PERSONAS:
                fila = dict(semana_inicio=inicio, semana=etiqueta, persona=persona,
                            tareas_json=contadores[(inicio, persona)])
                for col, ids in contadores[(inicio, persona)].items():
                    fila[col] = len(ids)
                filas.append(fila)
        return filas

    @api.model
    def _etapa_a_fecha(self, tarea, trackings, corte):
        """(id de etapa, momento en que entró en ella) de la tarea a la fecha de corte."""
        if not trackings:
            return tarea.stage_id.id, tarea.create_date
        previos = [t for t in trackings if t.create_date <= corte]
        if previos:
            return previos[-1].new_value_integer, previos[-1].create_date
        # Solo hay cambios posteriores: la etapa inicial es el origen del primero
        return trackings[0].old_value_integer, tarea.create_date
