from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EmailGroup(models.Model):
    _name = 'leulit_encuestas.email.group'
    _description = 'Grupo de correo para encuestas'

    name = fields.Char(string='Nombre', required=True)
    partner_ids = fields.Many2many('res.partner', string='Partners')
    external_emails = fields.Text(string='Correos externos',
                                  help='Correos adicionales separados por comas o nuevas líneas')
    company_id = fields.Many2one('res.company', string='Compañía')
    computed_emails = fields.Text(string='Emails (computado)', compute='_compute_computed_emails')

    @api.depends('partner_ids', 'external_emails')
    def _compute_computed_emails(self):
        for rec in self:
            emails = []
            for p in rec.partner_ids:
                if p.email:
                    emails.append(p.email.strip())
            if rec.external_emails:
                parts = [e.strip() for e in rec.external_emails.replace('\r', '\n').split('\n') if e.strip()]
                for part in parts:
                    for e in part.split(','):
                        e = e.strip()
                        if e:
                            emails.append(e)
            seen = set()
            uniq = []
            for e in emails:
                if e not in seen:
                    seen.add(e)
                    uniq.append(e)
            rec.computed_emails = '\n'.join(uniq)

    def get_emails_list(self):
        self.ensure_one()
        if not self.computed_emails:
            return []
        return [e.strip() for e in self.computed_emails.split('\n') if e.strip()]

    @api.constrains('external_emails')
    def _check_external_emails_format(self):
        for rec in self:
            if rec.external_emails:
                for e in [x.strip() for x in rec.external_emails.replace('\r', '\n').split('\n') if x.strip()]:
                    for sub in e.split(','):
                        email = sub.strip()
                        if email and '@' not in email:
                            raise ValidationError(_('El correo externo "%s" no parece válido') % email)
