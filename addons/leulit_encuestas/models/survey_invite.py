from odoo import api, fields, models


class SurveyInvite(models.TransientModel):
    _inherit = 'survey.invite'

    email_group_id = fields.Many2one('leulit_encuestas.email.group', string='Grupo de correo')

    @api.onchange('email_group_id')
    def _onchange_email_group_id(self):
        for rec in self:
            if not rec.email_group_id:
                continue
            partners = rec.email_group_id.partner_ids
            # set partner_ids to group partners
            rec.partner_ids = [(6, 0, partners.ids)]
            # compute external-only emails (exclude partner emails)
            external = rec.email_group_id.get_emails_list()
            partner_emails = [p.email for p in partners if p.email]
            extras = [e for e in external if e not in partner_emails]
            if extras:
                # populate the 'emails' free-text field with comma-separated emails
                rec.emails = ', '.join(extras)
