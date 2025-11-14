# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.exceptions import AccessError
from odoo.tools.translate import _


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def check(self, mode, values=None):
        """
        Sobrescribe el método check para permitir a usuarios RBase
        acceder a adjuntos sin res_model/res_id (adjuntos huérfanos).
        
        Esto es necesario porque en Odoo 17 el comportamiento cambió
        respecto a Odoo 14, donde estos adjuntos eran accesibles.
        """
        # Si el usuario tiene el grupo RBase, permitir acceso a adjuntos huérfanos
        if self.env.user.has_group('leulit.RBase'):
            # Permitir acceso para lectura y creación de adjuntos sin documento vinculado
            if mode in ('read', 'create'):
                return True
        
        # Para el resto de casos, usar el comportamiento estándar
        return super(IrAttachment, self).check(mode, values=values)
