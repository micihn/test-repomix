from odoo import api, fields, models, _
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_inter_company = fields.Boolean(
        string='Is Inter-Company Transaction',
        compute='_compute_is_inter_company',
        store=True
    )
    related_purchase_id = fields.Many2one(
        'purchase.order',
        string='Related Purchase Order',
        readonly=True
    )
    requires_approval = fields.Boolean(
        string='Requires Approval',
        compute='_compute_requires_approval'
    )
    inter_company_state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting_approval', 'Waiting Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Inter-Company Status', default='draft')

    @api.depends('partner_id')
    def _compute_is_inter_company(self):
        for order in self:
            order.is_inter_company = (
                order.partner_id.parent_id and 
                order.partner_id.parent_id.is_company and
                order.partner_id.parent_id != order.company_id
            )

    @api.depends('is_inter_company')
    def _compute_requires_approval(self):
        param = self.env['ir.config_parameter'].sudo()
        approval_required = param.get_param(
            'advance_inter_company_transaction.approval_required',
            'False'
        ).lower() == 'true'
        
        for order in self:
            order.requires_approval = order.is_inter_company and approval_required

    def action_confirm(self):
        for order in self:
            if order.is_inter_company:
                if order.requires_approval and order.inter_company_state != 'approved':
                    # Send notification to counter company's manager
                    counter_company = order.partner_id.parent_id
                    managers = self.env['res.users'].sudo().search([
                        ('groups_id', 'in', self.env.ref('advance_inter_company_transaction.group_inter_company_manager').id),
                        ('company_id', '=', counter_company.id)
                    ])
                    
                    message = _("""
                        <p>New inter-company order requires your approval:</p>
                        <ul>
                            <li><strong>Reference:</strong> %s</li>
                            <li><strong>Amount:</strong> %s %s</li>
                            <li><strong>Company:</strong> %s</li>
                        </ul>
                    """) % (
                        order.name,
                        order.currency_id.symbol,
                        order.amount_total,
                        order.company_id.name
                    )

                    for manager in managers:
                        order.message_post(
                            body=message,
                            message_type='notification',
                            subject=_('Inter-Company Order Approval Required'),
                            partner_ids=[(4, manager.partner_id.id)],
                            subtype_xmlid='mail.mt_note'
                        )
                    
                    order.inter_company_state = 'waiting_approval'
                    raise UserError(_('This inter-company order requires approval from %s.') % counter_company.name)
                
                self._create_inter_company_purchase_order()
        return super(SaleOrder, self).action_confirm()

    def _create_inter_company_purchase_order(self):
        self.ensure_one()
        if not self.is_inter_company:
            return

        PurchaseOrder = self.env['purchase.order'].sudo()
        company_partner = self.company_id.partner_id

        po_vals = {
            'partner_id': company_partner.id,
            'company_id': self.partner_id.parent_id.id,
            'origin': self.name,
            'notes': self.note,
            'user_id': self.partner_id.parent_id.inter_company_user_id.id,
        }

        purchase_order = PurchaseOrder.create(po_vals)

        for line in self.order_line:
            PurchaseOrder.order_line.create({
                'order_id': purchase_order.id,
                'product_id': line.product_id.id,
                'name': line.name,
                'product_qty': line.product_uom_qty,
                'price_unit': line.price_unit,
                'product_uom': line.product_uom.id,
                'date_planned': line.order_id.date_order,
            })

        self.related_purchase_id = purchase_order.id
        return purchase_order

    def action_approve_inter_company(self):
        self.ensure_one()
        if self.requires_approval:
            self.inter_company_state = 'approved'

    def action_reject_inter_company(self):
        self.ensure_one()
        if self.requires_approval:
            self.inter_company_state = 'rejected'

