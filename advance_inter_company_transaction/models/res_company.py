from odoo import api, fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    inter_company_user_id = fields.Many2one(
        'res.users',
        string='Inter-Company Transaction User',
        help='User responsible for processing inter-company transactions'
    )
