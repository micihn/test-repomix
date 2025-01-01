from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    intercompany_transaction_type = fields.Selection([
        ('sync_order', 'Synchronize Sales/Purchase'),
        ('sync_invoice', 'Synchronize Invoice/Bills')
    ], string='Inter Company Transaction Type', 
    config_parameter='intercompany_transaction.type')

    intercompany_validation_type = fields.Selection([
        ('auto_validate', 'Auto Validate'),
        ('no_validation', 'No Auto Validation'),
        ('dual_approval', 'Need Approval Both Side')
    ], string='Validation Type', 
    config_parameter='intercompany_transaction.validation_type')

    approval_manager_id = fields.Many2one(
        'res.users',
        string='Default Approval Manager',
        domain=[('share', '=', False)],
        config_parameter='intercompany_transaction.default_manager_id'
    )
