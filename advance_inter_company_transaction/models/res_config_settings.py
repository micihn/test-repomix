from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    inter_company_approval_required = fields.Boolean(
        string='Require Inter-Company Approval',
        config_parameter='advanced_inter_company.approval_required'
    )
