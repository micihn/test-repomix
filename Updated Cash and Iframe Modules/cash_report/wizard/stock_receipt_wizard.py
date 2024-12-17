from odoo import models, fields, api

class StockReceiptWizard(models.TransientModel):
    _name = 'stock.receipt.wizard'
    _description = 'Stock Receipt Report Wizard'

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

    def get_receipt_data(self, data):
        product_filter = ""
        sort_order = "rd.date, rd.product_code"
        params = [data['start_date'], data['end_date'], data['company_id']]

        if not data.get('all_products') and data.get('product_ids'):
            product_filter = "AND pp.id IN %s"
            params.append(tuple(data.get('product_ids')))

        if data.get('sort_by_reference'):
            sort_order = "rd.product_code, rd.date"

        query = """
            WITH receipt_data AS (
                SELECT 
                    pc.name as category_name,
                    pp.default_code as product_code,
                    COALESCE(pt.name->>'id_ID', pt.name->>'en_US') as product_name,
                    sm.reference as receipt_reference,
                    sp.note as note,
                    svl.create_date::date as date,
                    svl.quantity as quantity,
                    svl.unit_cost as unit_cost,
                    svl.value as total_value,
                    ROW_NUMBER() OVER(
                        PARTITION BY pc.name 
                        ORDER BY svl.create_date, pp.default_code
                    ) as line_no
                FROM stock_valuation_layer svl
                LEFT JOIN product_product pp ON svl.product_id = pp.id
                LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
                LEFT JOIN product_category pc ON pt.categ_id = pc.id
                LEFT JOIN stock_move sm ON svl.stock_move_id = sm.id
                LEFT JOIN stock_picking sp ON sm.picking_id = sp.id
                LEFT JOIN stock_picking_type spt ON sp.picking_type_id = spt.id
                WHERE svl.create_date::date BETWEEN %s AND %s
                AND svl.company_id = %s
                AND spt.code = 'incoming'
                """ + product_filter + """
            )
            SELECT 
                category_name,
                product_code,
                product_name,
                receipt_reference,
                note,
                date,
                quantity,
                unit_cost,
                total_value,
                line_no
            FROM receipt_data rd
            ORDER BY category_name, """ + sort_order
            
        self.env.cr.execute(query, params)
        return self.env.cr.dictfetchall()

    def generate_report(self):
        self.ensure_one()
        data = {
            'start_date': self.start_date,
            'end_date': self.end_date,
            'company_id': self.company_id.id,
            'all_products': self.all_products,
            'product_ids': self.product_ids.ids if self.product_ids else [],
            'sort_by_reference': self.sort_by_reference,
        }
        return self.env.ref('cash_report.action_stock_receipt_report').report_action(self, data=data)