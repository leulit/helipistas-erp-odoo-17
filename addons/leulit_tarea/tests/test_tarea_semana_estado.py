# -*- encoding: utf-8 -*-
from datetime import datetime
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.leulit_tarea.models import tarea_semana_estado as modulo

# Semana en curso: lunes 14/09/2026 - hoy miércoles 16/09/2026. Semana anterior: 07/09 - 13/09.
HOY = datetime(2026, 9, 16, 12, 0, 0)
SEMANA_ANT = datetime(2026, 9, 9, 10, 0, 0)
SEMANA_ACT = datetime(2026, 9, 15, 10, 0, 0)


@tagged('post_install', '-at_install')
class TestTareaSemanaEstado(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Users = cls.env['res.users'].with_context(no_reset_password=True)
        cls.emilio = Users.create({'name': 'T Emilio', 'login': 't_emilio_sem'})
        cls.pau = Users.create({'name': 'T Pau', 'login': 't_pau_sem'})
        cls.tercero = Users.create({'name': 'T Tercero', 'login': 't_tercero_sem'})
        Type = cls.env['project.task.type']
        cls.st_pend = Type.create({'name': 'Pendiente'})
        cls.st_proc = Type.create({'name': 'En proceso'})
        cls.st_real = Type.create({'name': 'Realizada'})
        cls.campo = cls.env['ir.model.fields']._get('project.task', 'stage_id')
        patcher = patch.multiple(modulo, USER_EMILIO=cls.emilio.id, USER_PAU=cls.pau.id)
        patcher.start()
        cls.addClassCleanup(patcher.stop)

    def _tarea(self, users, stage, creada):
        tarea = self.env['project.task'].with_context(tracking_disable=True).create({
            'name': 'T', 'user_ids': [(6, 0, users.ids)], 'stage_id': stage.id,
        })
        self.env.cr.execute('UPDATE project_task SET create_date=%s WHERE id=%s', (creada, tarea.id))
        tarea.invalidate_recordset()
        return tarea

    def _cambio(self, tarea, de, a, cuando):
        msg = self.env['mail.message'].create({
            'model': 'project.task', 'res_id': tarea.id, 'message_type': 'notification',
        })
        tr = self.env['mail.tracking.value'].create({
            'mail_message_id': msg.id, 'field_id': self.campo.id,
            'old_value_integer': de.id, 'new_value_integer': a.id,
        })
        self.env.cr.execute('UPDATE mail_tracking_value SET create_date=%s WHERE id=%s', (cuando, tr.id))
        self.env['mail.tracking.value'].invalidate_model()

    def _fila(self, filas, inicio, persona):
        return next(f for f in filas if f['semana_inicio'].isoformat() == inicio and f['persona'] == persona)

    def test_ejemplo_usuario(self):
        # Semana anterior: 4 tareas de Emilio creadas en Pendiente; la siguiente pasan a Realizada
        for _i in range(4):
            t = self._tarea(self.emilio, self.st_real, SEMANA_ANT)
            self._cambio(t, self.st_pend, self.st_real, SEMANA_ACT)
        # 2 nuevas creadas y cerradas la semana siguiente
        for _i in range(2):
            t = self._tarea(self.emilio, self.st_real, SEMANA_ACT)
            self._cambio(t, self.st_pend, self.st_real, SEMANA_ACT)
        self._tarea(self.emilio, self.st_proc, SEMANA_ACT)
        self._tarea(self.emilio, self.st_pend, SEMANA_ACT)

        filas = self.env['leulit.tarea.semana.estado']._calcular_filas(HOY)
        self.assertEqual(len(filas), 12 * 3)
        act = self._fila(filas, '2026-09-14', modulo.PERSONA_EMILIO)
        self.assertEqual((act['pendiente'], act['en_proceso'], act['pospuesta'], act['realizada']), (1, 1, 0, 6))
        ant = self._fila(filas, '2026-09-07', modulo.PERSONA_EMILIO)
        self.assertEqual((ant['pendiente'], ant['en_proceso'], ant['pospuesta'], ant['realizada']), (4, 0, 0, 0))
        self.assertIn('hasta hoy', act['semana'])

    def test_cerrada_semana_anterior_no_cuenta_en_la_siguiente(self):
        t = self._tarea(self.emilio, self.st_real, SEMANA_ANT)
        self._cambio(t, self.st_pend, self.st_real, SEMANA_ANT)
        filas = self.env['leulit.tarea.semana.estado']._calcular_filas(HOY)
        self.assertEqual(self._fila(filas, '2026-09-07', modulo.PERSONA_EMILIO)['realizada'], 1)
        self.assertEqual(self._fila(filas, '2026-09-14', modulo.PERSONA_EMILIO)['realizada'], 0)

    def test_persona(self):
        self._tarea(self.emilio | self.tercero, self.st_pend, SEMANA_ACT)
        self._tarea(self.emilio | self.pau, self.st_pend, SEMANA_ACT)
        self._tarea(self.tercero, self.st_pend, SEMANA_ACT)
        filas = self.env['leulit.tarea.semana.estado']._calcular_filas(HOY)
        self.assertEqual(self._fila(filas, '2026-09-14', modulo.PERSONA_EMILIO)['pendiente'], 1)
        self.assertEqual(self._fila(filas, '2026-09-14', modulo.PERSONA_AMBOS)['pendiente'], 1)
        self.assertEqual(self._fila(filas, '2026-09-14', modulo.PERSONA_PAU)['pendiente'], 0)
