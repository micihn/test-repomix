from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    is_inter_company = fields.Boolean(
        string='Is Inter-Company Transaction',
        compute='_compute_is_inter_company',
        store=True
    )
    related_sale_id = fields.Many2one(
        'sale.order',
        string='Related Sale Order',
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
                order.partner_id.is_company and
                order.partner_id != order.company_id
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

    def button_confirm(self):
        for order in self:
            if order.is_inter_company:
                if order.requires_approval and order.inter_company_state != 'approved':
                    # Send notification to counter company's manager
                    counter_company = order.partner_id
                    managers = self.env['res.users'].sudo().search([
                        ('groups_id', 'in', self.env.ref('advance_inter_company_transaction.group_inter_company_manager').id),
                        ('company_id', '=', counter_company.id)
                    ])
                    
                    message = _("""
                        <p>New inter-company purchase order requires your approval:</p>
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
                            subject=_('Inter-Company Purchase Order Approval Required'),
                            partner_ids=[(4, manager.partner_id.id)],
                            subtype_xmlid='mail.mt_note'
                        )
                    
                    order.inter_company_state = 'waiting_approval'
                    raise UserError(_('This inter-company order requires approval from %s.') % counter_company.name)
                
                self._create_inter_company_sale_order()
        return super(PurchaseOrder, self).button_confirm()

    def _create_inter_company_sale_order(self):
        self.ensure_one()
        if not self.is_inter_company:
            return

        SaleOrder = self.env['sale.order'].sudo()
        
        # Get the company record instead of partner
        counter_company = self.partner_id
        
        # Get the responsible user from company settings
        responsible_user = counter_company.inter_company_user_id or self.env.user

        so_vals = {
            'partner_id': self.company_id.partner_id.id,
            'company_id': counter_company.id,
            'origin': self.name,
            'note': self.notes,
            'user_id': responsible_user.id,  # Use the found responsible user
            'team_id': self.env['crm.team'].sudo().search(
                [('company_id', '=', counter_company.id)], 
                limit=1
            ).id
        }

        sale_order = SaleOrder.create(so_vals)

        for line in self.order_line:
            SaleOrder.order_line.create({
                'order_id': sale_order.id,
                'product_id': line.product_id.id,
                'name': line.name,
                'product_uom_qty': line.product_qty,
                'price_unit': line.price_unit,
                'product_uom': line.product_uom.id,
            })

        self.related_sale_id = sale_order.id
        return sale_order

    def action_approve_inter_company(self):
        self.ensure_one()
        if self.requires_approval:
            self.inter_company_state = 'approved'

    def action_reject_inter_company(self):
        self.ensure_one()
        if self.requires_approval:
            self.inter_company_state = 'rejected'