from odoo import models, fields, api
from odoo.exceptions import AccessError

class IFrameDashboard(models.Model):
    _name = 'iframe.dashboard'
    _description = 'IFrame Dashboard'

    name = fields.Char(string='Dashboard Name', required=True)
    url = fields.Char(string='Dashboard URL', required=True)
    is_active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    user_ids = fields.Many2many('res.users', string='Authorized Users')

    def action_view_dashboard(self):
        self.ensure_one()
        if not self.user_has_access():
            raise AccessError("You don't have access to this dashboard.")
        return {
            'type': 'ir.actions.act_url',
            'url': self.url,
            'target': 'new',
        }

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        domain += [('company_id', 'in', [self.env.company.id, False])]
        return super(IFrameDashboard, self).search_read(domain, fields, offset, limit, order)

    def user_has_access(self):
        self.ensure_one()
        return not self.user_ids or self.env.user in self.user_ids

