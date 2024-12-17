from odoo import models, fields, api

class SparepartReturnWizard(models.TransientModel):
    _name = 'sparepart.return.wizard'
    _description = 'Laporan Pengeluaran Spare Parts (RETUR) Wizard'

    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=fields.Date.context_today
    )
    end_date = fields.Date(
        string='End Date',
        required=True,
        default=fields.Date.context_today
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    all_products = fields.Boolean(
        string='Semua Barang',
        default=True
    )
    show_subcategory = fields.Boolean(
        string='Tampilkan Sub Kategori',
        default=False
    )
    product_ids = fields.Many2many(
        'product.product',
        string='Products',
        domain="[('type', '!=', 'service')]"
    )
    sort_by_reference = fields.Boolean(
        string='Urutkan Berdasarkan Referensi Internal',
        default=False
    )

    @api.onchange('all_products')
    def _onchange_all_products(self):
        if self.all_products:
            self.product_ids = False

    def get_sparepart_return_data(self, data):
        picking_type = self.env['stock.picking.type'].search([
            ('name', '=', 'Keluar Barang'),
            ('company_id', '=', data['company_id'])
        ], limit=1)
        
        if not picking_type:
            raise UserError('Picking type "Keluar Barang" not found.')

        product_filter = ""
        sort_order = "date, product_code"
        params = [data.get('show_subcategory', False)]

        if not data.get('all_products') and data.get('product_ids'):
            product_filter = "AND pp.id = ANY(%s)"
            params.extend([
                data['start_date'],
                data['end_date'],
                data['company_id'],
                picking_type.id,
                data.get('product_ids')
            ])
        else:
            params.extend([
                data['start_date'],
                data['end_date'],
                data['company_id'],
                picking_type.id
            ])

        query = """
            WITH move_data AS (
                SELECT 
                    fst.name->>'en_US' as service_type,
                    CASE WHEN %s THEN LEFT(pt.default_code, 7) ELSE '' END as subcategory,
                    pt.default_code as product_code,
                    COALESCE(pt.name->>'id_ID', pt.name->>'en_US') as product_name,
                    sp.name as receipt_reference,
                    sp.origin as origin,
                    sm.nomor_kendaraan as truck_number,
                    fvls.description as description,
                    pc.name as category_name,
                    svl.create_date::date as date,
                    ABS(svl.quantity) as quantity,
                    svl.unit_cost as unit_cost,
                    ABS(svl.value) as total_value,
                    ROW_NUMBER() OVER(
                        PARTITION BY 
                            fst.name->>'en_US', 
                            CASE WHEN %s THEN LEFT(pt.default_code, 7) ELSE '' END
                        ORDER BY svl.create_date, pt.default_code
                    ) as line_no
                FROM stock_valuation_layer svl
                JOIN product_product pp ON svl.product_id = pp.id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                JOIN product_category pc ON pt.categ_id = pc.id
                JOIN stock_move sm ON svl.stock_move_id = sm.id
                JOIN stock_picking sp ON sm.picking_id = sp.id
                JOIN stock_picking_type spt ON sp.picking_type_id = spt.id
                LEFT JOIN fleet_vehicle_log_services fvls ON sp.fleet_service_id = fvls.id
                LEFT JOIN fleet_service_type fst ON fvls.service_type_id = fst.id
                WHERE 
                    svl.create_date::date BETWEEN %s AND %s
                    AND svl.company_id = %s
                    AND spt.id = %s
                    AND sp.origin ILIKE '%Return%'
                    """ + product_filter + """
            )
            SELECT * FROM move_data
            ORDER BY service_type, subcategory, """ + sort_order
        
        params.insert(1, params[0])  # Add the subcategory parameter again for the second CASE WHEN
        self.env.cr.execute(query, tuple(params))
        return self.env.cr.dictfetchall()

    def generate_report(self):
        self.ensure_one()
        data = {
            'start_date': self.start_date,
            'end_date': self.end_date,
            'company_id': self.company_id.id,
            'all_products': self.all_products,
            'show_subcategory': self.show_subcategory,
            'product_ids': self.product_ids.ids if self.product_ids else [],
            'sort_by_reference': self.sort_by_reference,
        }
        return self.env.ref('cash_report.action_sparepart_return_report').report_action(self, data=data)