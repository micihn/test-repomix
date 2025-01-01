from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'intercompany.mixin']

    is_intercompany_transaction = fields.Boolean(
        string='Inter Company Transaction',
        readonly=True,
        copy=False
    )
    
    intercompany_purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Related Purchase Order',
        readonly=True,
        copy=False
    )

    auto_generated = fields.Boolean('Auto Generated', readonly=True, copy=False)

    def _prepare_intercompany_purchase_order_data(self):
        """Prepare purchase order data for inter-company transaction"""
        self.ensure_one()
        company_partner = self.company_id.partner_id
        return {
            'partner_id': company_partner.id,
            'company_id': self.partner_id.company_id.id,
            'is_intercompany_transaction': True,
            'origin': self.name,
            'partner_ref': self.name,
            'order_line': [(0, 0, {
                'product_id': line.product_id.id,
                'name': line.name,
                'product_qty': line.product_uom_qty,
                'price_unit': line.price_unit,
                'product_uom': line.product_uom.id,
                'date_planned': line.order_id.date_order,
            }) for line in self.order_line],
        }

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            _logger.info('Creating SO: Partner Company: %s, Current Company: %s', 
                        record.partner_id.company_id, record.company_id)
            if not record.auto_generated:
                company_id = record.partner_id.company_id
                if company_id and company_id != record.company_id:
                    config_param = self.env['ir.config_parameter'].sudo()
                    transaction_type = config_param.get_param('intercompany_transaction.type')
                    _logger.info('Transaction Type from config: %s', transaction_type)
                    if transaction_type == 'sync_order':
                        record._create_counterpart_purchase_order()
        return records

    def _create_counterpart_purchase_order(self):
        """Create corresponding purchase order in partner's company"""
        self.ensure_one()
        if not self.partner_id.company_id:
            return

        PurchaseOrder = self.env['purchase.order'].with_company(self.partner_id.company_id.id)
        # Prepare order lines
        order_lines = []
        for line in self.order_line:
            order_lines.append((0, 0, {
                'name': line.name,
                'product_id': line.product_id.id,
                'product_qty': line.product_uom_qty,
                'product_uom': line.product_uom.id,
                'price_unit': line.price_unit,
                'date_planned': fields.Datetime.now(),
            }))

        # Create purchase order
        po_vals = {
            'partner_id': self.company_id.partner_id.id,  # Company A's partner as vendor
            'company_id': self.partner_id.company_id.id,  # Company B
            'is_intercompany_transaction': True,
            'auto_generated': True,
            'origin': self.name,
            'order_line': order_lines,
        }

        purchase_order = PurchaseOrder.create(po_vals)
        self.write({
            'is_intercompany_transaction': True,
            'intercompany_purchase_order_id': purchase_order.id
        })
        return purchase_order

    def action_confirm(self):
        """Override to handle inter-company validation logic"""
        for order in self:
            if order.is_intercompany_transaction:
                validation_type = order._get_validation_type()
                
                if validation_type == 'auto_validate':
                    if not order.intercompany_purchase_order_id:
                        order._create_counterpart_purchase_order()
                    order.intercompany_purchase_order_id.button_confirm()
                    
                elif validation_type == 'dual_approval':
                    if order.intercompany_state != 'approved':
                        order.intercompany_state = 'waiting_approval'
                        return
                    
                    if not order.intercompany_purchase_order_id:
                        order._create_counterpart_purchase_order()
                        order.intercompany_purchase_order_id.intercompany_state = 'waiting_approval'
                    elif order.intercompany_purchase_order_id.intercompany_state == 'approved':
                        order.intercompany_purchase_order_id.button_confirm()
                
                else:  # no_validation
                    if not order.intercompany_purchase_order_id:
                        order._create_counterpart_purchase_order()
            
            super(SaleOrder, order).action_confirm()