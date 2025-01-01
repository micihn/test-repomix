from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class InterCompanyMixin(models.AbstractModel):
    _name = 'intercompany.mixin'
    _description = 'Inter Company Transaction Mixin'

    is_intercompany_transaction = fields.Boolean(
        string='Inter Company Transaction',
        readonly=True,
        copy=False
    )

    intercompany_state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting_approval', 'Waiting Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Inter Company Status', default='draft', tracking=True)

    def _get_validation_type(self):
        return self.env['ir.config_parameter'].sudo().get_param('intercompany_transaction.validation_type')

    def _check_approval_rights(self):
        param = self.env['ir.config_parameter'].sudo().get_param('intercompany_transaction.manager_ids')
        if not param:
            raise ValidationError(_('No approval managers configured for inter-company transactions.'))
        manager_ids = [int(x) for x in param.split(',') if x]
        if not manager_ids or self.env.user.id not in manager_ids:
            raise ValidationError(_('You are not authorized to approve inter-company transactions.'))
        return True

    def action_approve_intercompany(self):
        self.ensure_one()
        self._check_approval_rights()
        self.intercompany_state = 'approved'
        return True

    def action_reject_intercompany(self):
        self.ensure_one()
        self._check_approval_rights()
        self.intercompany_state = 'rejected'
        return True
