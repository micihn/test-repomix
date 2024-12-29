from odoo import api, fields, models, _

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_inter_company = fields.Boolean(
        string='Is Inter-Company Transfer',
        compute='_compute_is_inter_company',
        store=True
    )
    related_picking_id = fields.Many2one(
        'stock.picking',
        string='Related Transfer',
        readonly=True
    )
    x_nomor_kendaraan = fields.Char(
        string='Nomor Kendaraan',
        tracking=True,
    )

    @api.depends('sale_id', 'purchase_id')
    def _compute_is_inter_company(self):
        for picking in self:
            picking.is_inter_company = (
                (picking.sale_id and picking.sale_id.is_inter_company) or
                (picking.purchase_id and picking.purchase_id.is_inter_company)
            )

    def _create_backorder(self):
        backorders = super(StockPicking, self)._create_backorder()
        for backorder in backorders:
            if backorder.is_inter_company and backorder.related_picking_id:
                related_backorder = backorder.related_picking_id._create_backorder()
                if related_backorder:
                    backorder.related_picking_id = related_backorder.id
        return backorders

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        for picking in self:
            if picking.is_inter_company:
                if not picking.related_picking_id:
                    picking._create_inter_company_picking()
        return res

    def _create_inter_company_picking(self):
        self.ensure_one()
        if not self.is_inter_company:
            return

        Picking = self.env['stock.picking'].sudo()
        
        # Determine counterpart company
        if self.sale_id:
            counterpart_company = self.partner_id.parent_id
        else:  # purchase_id
            counterpart_company = self.partner_id

        # Get warehouse
        warehouse = self.env['stock.warehouse'].sudo().search([
            ('company_id', '=', counterpart_company.id)
        ], limit=1)

        if not warehouse:
            return

        # Determine picking type based on operation
        if self.sale_id:
            picking_type = warehouse.in_type_id
        else:  # purchase_id
            picking_type = warehouse.out_type_id

        vals = {
            'partner_id': self.company_id.partner_id.id,
            'company_id': counterpart_company.id,
            'picking_type_id': picking_type.id,
            'location_id': picking_type.default_location_src_id.id,
            'location_dest_id': picking_type.default_location_dest_id.id,
            'origin': self.name,
            'related_picking_id': self.id,
            'x_nomor_kendaraan': self.x_nomor_kendaraan,  # Copy vehicle number to related picking
        }

        if self.sale_id:
            vals['purchase_id'] = self.sale_id.related_purchase_id.id
        else:  # purchase_id
            vals['sale_id'] = self.purchase_id.related_sale_id.id

        picking = Picking.create(vals)

        for move in self.move_lines:
            move_vals = {
                'name': move.name,
                'product_id': move.product_id.id,
                'product_uom_qty': move.product_uom_qty,
                'product_uom': move.product_uom.id,
                'picking_id': picking.id,
                'location_id': picking.location_id.id,
                'location_dest_id': picking.location_dest_id.id,
                'company_id': picking.company_id.id,
            }
            Picking.move_lines.create(move_vals)

        self.related_picking_id = picking.id
        return picking