from odoo import models, fields, api

class SetoranLangsungWizard(models.TransientModel):
    _name = 'setoran.langsung.wizard'
    _description = 'Laporan Harian Setoran Langsung Wizard'

    start_date = fields.Date(
        string='Tanggal Mulai',
        required=True,
        default=fields.Date.context_today
    )
    end_date = fields.Date(
        string='Tanggal Akhir',
        required=True,
        default=fields.Date.context_today
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )

    def generate_report(self):
        self.ensure_one()
        data = {
            'start_date': self.start_date,
            'end_date': self.end_date,
            'company_id': self.company_id.id,
        }
        return self.env.ref('cash_report.action_report_setoran_langsung').report_action(self, data=data)

    def get_setoran_langsung_data(self, data):
        query = """
            WITH setoran_data AS (
                SELECT 
                    os.kode_oper_setoran as kode,
                    os.tanggal_stlo as tanggal,
                    os.kendaraan,
                    os.total_oper_order as total_order,
                    COALESCE(SUM(bf.nominal), 0) as biaya_fee,
                    COALESCE(STRING_AGG(DISTINCT rp_fee.name, ', '), '') as fee_contact_names,
                    COALESCE(SUM(bp.nominal), 0) as biaya_pembelian,
                    COALESCE(STRING_AGG(DISTINCT rp_sup.name, ', '), '') as supplier_names,
                    COALESCE(SUM(op.total_ongkos), 0) as total_ongkos,
                    COALESCE(STRING_AGG(DISTINCT rp_cust.name, ', '), '') as customer_names,
                    COALESCE(rp_vendor.name, '') as vendor_name,
                    os.sisa
                FROM oper_setoran os
                LEFT JOIN biaya_pembelian_oper_setoran_rel bposr ON os.id = bposr.oper_setoran_id
                LEFT JOIN biaya_pembelian bp ON bposr.biaya_pembelian_id = bp.id
                LEFT JOIN biaya_fee_oper_setoran_rel bfosr ON os.id = bfosr.oper_setoran_id
                LEFT JOIN biaya_fee bf ON bfosr.biaya_fee_id = bf.id
                LEFT JOIN detail_order_setoran dos ON os.id = dos.oper_setoran
                LEFT JOIN order_pengiriman op ON dos.order_pengiriman = op.id
                LEFT JOIN res_partner rp_vendor ON os.vendor_pa = rp_vendor.id
                LEFT JOIN res_partner rp_sup ON bp.supplier = rp_sup.id
                LEFT JOIN res_partner rp_fee ON bf.fee_contact = rp_fee.id
                LEFT JOIN res_partner rp_cust ON op.customer = rp_cust.id
                WHERE 
                    os.tanggal_stlo BETWEEN %s AND %s
                    AND os.company_id = %s
                GROUP BY
                    os.id,
                    os.kode_oper_setoran,
                    os.tanggal_stlo,
                    os.kendaraan,
                    os.total_oper_order,
                    rp_vendor.name,
                    os.sisa
                ORDER BY
                    os.tanggal_stlo, os.kode_oper_setoran
            )
            SELECT * FROM setoran_data
        """
        
        self.env.cr.execute(query, (data['start_date'], data['end_date'], data['company_id']))
        return self.env.cr.dictfetchall()