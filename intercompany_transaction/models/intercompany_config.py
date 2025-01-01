from odoo import api, fields, models

class InterCompanyConfig(models.Model):
    _name = 'intercompany.config'
    _description = 'Inter Company Configuration'

    name = fields.Char(string='Name', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True)
    approval_manager_id = fields.Many2one(
        'res.users',
        string='Approval Manager',
        domain=[('share', '=', False)],
        required=True
    )
