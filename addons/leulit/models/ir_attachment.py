# -*- coding: utf-8 -*-
from collections import defaultdict
from odoo import models, api
from odoo.exceptions import AccessError
from odoo.tools.translate import _


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def check(self, mode, values=None):
        """
        Sobrescribe completamente el método check para permitir a usuarios RBase
        acceder a adjuntos sin res_model/res_id (adjuntos huérfanos).
        
        Esto es necesario porque en Odoo 17 el comportamiento cambió
        respecto a Odoo 14, donde estos adjuntos eran accesibles.
        """
        if self.env.is_superuser():
            return True
            
        # Always require an internal user (aka, employee) to access to a attachment
        if not (self.env.is_admin() or self.env.user._is_internal()):
            raise AccessError(_("Perdon, you are not allowed to access this document."))
            
        # collect the records to check (by model)
        model_ids = defaultdict(set)            # {model_name: set(ids)}
        if self:
            self.env['ir.attachment'].flush_model(['res_model', 'res_id', 'create_uid', 'public', 'res_field'])
            self._cr.execute('SELECT res_model, res_id, create_uid, public, res_field FROM ir_attachment WHERE id IN %s', [tuple(self.ids)])
            for res_model, res_id, create_uid, public, res_field in self._cr.fetchall():
                if public and mode == 'read':
                    continue
                if not self.env.is_system():
                    # MODIFICACIÓN: Permitir a usuarios RBase acceder a adjuntos huérfanos
                    if not res_id and create_uid != self.env.uid:
                        if not self.env.user.has_group('leulit.RBase'):
                            raise AccessError(_("Perdon, you are not allowed to access this document."))
                    if res_field:
                        field = self.env[res_model]._fields[res_field]
                        if field.groups:
                            if not self.env.user.user_has_groups(field.groups):
                                raise AccessError(_("Perdon, you are not allowed to access this document."))
                if not (res_model and res_id):
                    continue
                model_ids[res_model].add(res_id)
                
        if values and values.get('res_model') and values.get('res_id'):
            model_ids[values['res_model']].add(values['res_id'])

        # check access rights on the records
        for res_model, res_ids in model_ids.items():
            # ignore attachments that are not attached to a resource anymore
            # when checking access rights (resource was deleted but attachment was not)
            if res_model not in self.env:
                continue
            if res_model == 'res.users' and len(res_ids) == 1 and self.env.uid == list(res_ids)[0]:
                # by default a user cannot write on itself, despite the list of writeable fields
                # e.g. in the case of a user inserting an image into his image signature
                # we need to bypass this check which would needlessly throw us away
                continue
            records = self.env[res_model].browse(res_ids).exists()
            # For related models, check if we can write to the model, as unlinking
            # and creating attachments can be seen as an update to the model
            access_mode = 'write' if mode in ('create', 'unlink') else mode
            records.check_access_rights(access_mode)
            records.check_access_rule(access_mode)
