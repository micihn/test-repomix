from odoo import api, fields, models

class PurchaseOrder(models.Model):
    _name = 'purchase.order'
    _inherit = ['purchase.order', 'intercompany.mixin']

    is_intercompany_transaction = fields.Boolean(
        string='Inter Company Transaction',
        readonly=True,
        copy=False
    )
    
    intercompany_sale_order_id = fields.Many2one(
        'sale.order',
        string='Related Sale Order',
        readonly=True,
        copy=False
    )

    auto_generated = fields.Boolean('Auto Generated', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if not record.auto_generated:  # Prevent infinite loop
                company_id = record.partner_id.company_id
                if company_id and company_id != record.company_id:
                    config_param = self.env['ir.config_parameter'].sudo()
                    if config_param.get_param('intercompany_transaction.type') == 'sync_order':
                        record._create_counterpart_sale_order()
        return records

    def _create_counterpart_sale_order(self):
        """Create corresponding sale order in partner's company"""
        self.ensure_one()
        if not self.partner_id.company_id:
            return

        SaleOrder = self.env['sale.order'].with_company(self.partner_id.company_id.id)
        # Prepare order lines
        order_lines = []
        for line in self.order_line:
            order_lines.append((0, 0, {
                'name': line.name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.product_qty,
                'product_uom': line.product_uom.id,
                'price_unit': line.price_unit,
            }))

        # Create sale order
        so_vals = {
            'partner_id': self.company_id.partner_id.id,  # Company A's partner as customer
            'company_id': self.partner_id.company_id.id,  # Company B
            'is_intercompany_transaction': True,
            'auto_generated': True,
            'origin': self.name,
            'order_line': order_lines,
        }

        sale_order = SaleOrder.create(so_vals)
        self.write({
            'is_intercompany_transaction': True,
            'intercompany_sale_order_id': sale_order.id
        })
        return sale_order

