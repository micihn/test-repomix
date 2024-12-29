from odoo import api, fields, models, _
from odoo.exceptions import UserError

class InterCompanyApproveWizard(models.TransientModel):
    _name = 'inter.company.approve.wizard'
    _description = 'Inter-Company Approval Wizard'

    order_id = fields.Many2one('sale.order', string='Sale Order')
    purchase_id = fields.Many2one('purchase.order', string='Purchase Order')
    note = fields.Text(string='Approval Note')
    approval_type = fields.Selection([
        ('approve', 'Approve'),
        ('reject', 'Reject'),
    ], string='Action', required=True, default='approve')
    
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_model = self._context.get('active_model')
        active_id = self._context.get('active_id')

        if active_id:
            if active_model == 'sale.order':
                res['order_id'] = active_id
                order = self.env['sale.order'].browse(active_id)
                if not order.is_inter_company:
                    raise UserError(_('Selected order is not an inter-company transaction.'))
            elif active_model == 'purchase.order':
                res['purchase_id'] = active_id
                order = self.env['purchase.order'].browse(active_id)
                if not order.is_inter_company:
                    raise UserError(_('Selected order is not an inter-company transaction.'))
        return res

    def action_process(self):
        self.ensure_one()
        if self.approval_type not in ['approve', 'reject']:
            raise UserError(_('Invalid approval action.'))

        # Process Sale Order
        if self.order_id:
            if self.approval_type == 'approve':
                self.order_id.action_approve_inter_company()
            else:
                self.order_id.action_reject_inter_company()
            self._send_notification(self.order_id, is_approved=(self.approval_type == 'approve'))

        # Process Purchase Order
        if self.purchase_id:
            if self.approval_type == 'approve':
                self.purchase_id.action_approve_inter_company()
            else:
                self.purchase_id.action_reject_inter_company()
            self._send_notification(self.purchase_id, is_approved=(self.approval_type == 'approve'))

        return {'type': 'ir.actions.act_window_close'}

    def _send_notification(self, order, is_approved):
        """Send internal notification about approval decision"""
        status = _('approved') if is_approved else _('rejected')
        message = _("""
            <p>Inter-company order has been <strong>%s</strong></p>
            <ul>
                <li><strong>Reference:</strong> %s</li>
                <li><strong>Amount:</strong> %s %s</li>
            </ul>
        """) % (
            status,
            order.name,
            order.currency_id.symbol,
            order.amount_total
        )

        if self.note:
            message += _('<p><strong>Note:</strong> %s</p>') % self.note

        # Post message using Odoo's chatter
        order.message_post(
            body=message,
            message_type='notification',
            subject=_('Inter-Company Order %s') % status,
            partner_ids=[(4, order.user_id.partner_id.id)],  # Notify the order creator
            subtype_xmlid='mail.mt_note'
        )