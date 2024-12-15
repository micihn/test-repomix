from odoo import models, fields, api

class SetoranReportWizard(models.TransientModel):
    _name = 'setoran.report.wizard'
    _description = 'Laporan Harian Setoran Wizard'

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
            'report_type': 'qweb-pdf',
        }
        return self.env.ref('cash_report.action_report_setoran').with_context(
            start_date=self.start_date,
            end_date=self.end_date,
            company_id=self.company_id.id
        ).report_action(self, data=data)

    def get_setoran_data(self, data):
        start_date = data.get('start_date') or self.start_date
        end_date = data.get('end_date') or self.end_date
        company_id = data.get('company_id') or self.company_id.id

        query = """
            WITH setoran_data AS (
                SELECT 
                    os.id as setoran_id,
                    os.tanggal_st as tanggal,
                    os.kode_order_setoran as kode,
                    COALESCE(koms.nominal, 0) as komisi_sopir,
                    COALESCE(komk.nominal, 0) as komisi_kenek,
                    COALESCE(os.total_pengeluaran, 0) as total_pengeluaran,
                    COALESCE(SUM(bp.nominal), 0) as biaya_pembelian,
                    COALESCE(SUM(bf.nominal), 0) as biaya_fee
                FROM order_setoran os
                LEFT JOIN hr_employee_komisi_sejarah koms ON os.komisi_sopir_id = koms.id
                LEFT JOIN hr_employee_komisi_sejarah komk ON os.komisi_kenek_id = komk.id
                LEFT JOIN biaya_pembelian_order_setoran_rel bposr ON os.id = bposr.order_setoran_id
                LEFT JOIN biaya_pembelian bp ON bposr.biaya_pembelian_id = bp.id
                LEFT JOIN biaya_fee_order_setoran_rel bfosr ON os.id = bfosr.order_setoran_id
                LEFT JOIN biaya_fee bf ON bfosr.biaya_fee_id = bf.id
                WHERE 
                    os.tanggal_st BETWEEN %s AND %s
                    AND os.company_id = %s
                GROUP BY
                    os.id,
                    os.tanggal_st,
                    os.kode_order_setoran,
                    koms.nominal,
                    komk.nominal,
                    os.total_pengeluaran
            )
            SELECT 
                sd.*,
                uj.uang_jalan_name as uang_jalan,
                COALESCE(uj.total, 0) as uang_jalan_total
            FROM setoran_data sd
            LEFT JOIN detail_list_uang_jalan dluj ON sd.setoran_id = dluj.order_setoran
            LEFT JOIN uang_jalan uj ON dluj.uang_jalan_name = uj.id
            ORDER BY
                sd.tanggal,
                sd.kode,
                uj.uang_jalan_name
        """
        
        self.env.cr.execute(query, (start_date, end_date, company_id))
        return self.env.cr.dictfetchall()