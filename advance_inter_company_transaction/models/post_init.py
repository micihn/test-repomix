from odoo import api, models

class PostInit(models.AbstractModel):
    _name = 'advance_inter_company_transaction.post_init'
    _description = 'Post Init Hook'

    def set_default_config(self):
        """Set default configuration after install/upgrade"""
        config = self.env['ir.config_parameter'].sudo()
        
        # Try to get existing value
        approval_required = config.get_param(
            'advance_inter_company_transaction.approval_required',
            default='True'
        )
        
        # Update or create the parameter
        config.set_param('advance_inter_company_transaction.approval_required', approval_required)

# Override config settings
class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    inter_company_approval_required = fields.Boolean(
        string='Require Inter-Company Approval',
        config_parameter='advance_inter_company_transaction.approval_required'
    )