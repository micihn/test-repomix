from odoo import models, fields, api

class EmployeeRekapWizard(models.TransientModel):
    _name = 'employee.rekap.wizard'
    _description = 'Laporan Karyawan Rekap Wizard'

    employee_ids = fields.Many2many(
        'hr.employee',
        string='Employees',
        help="Leave empty to include all employees"
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
            'employee_ids': self.employee_ids.ids if self.employee_ids else [],
            'company_id': self.company_id.id,
        }
        return self.env.ref('cash_report.action_report_employee_rekap').report_action(self, data=data)

    def get_employee_rekap_data(self, data):
        employee_filter = ""
        params = [data['company_id']]
        
        if data.get('employee_ids'):
            employee_filter = "AND he.id IN %s"
            params.append(tuple(data['employee_ids']))

        query = """
            SELECT 
                he.identification_id,
                he.name as employee_name,
                COALESCE(SUM(he.hutang_karyawan), 0) as total_hutang
            FROM hr_employee he
            LEFT JOIN kasbon_karyawan kk ON kk.nama_karyawan = he.id
            LEFT JOIN kasbon_karyawan_journal_entry_hutang_rel kkjh 
                ON kk.id = kkjh.kasbon_karyawan_id
            LEFT JOIN kasbon_karyawan_journal_entry_pelunasan_hutang_rel kkjp 
                ON kk.id = kkjp.kasbon_karyawan_id
            WHERE 
                kk.company_id = %s
                """ + employee_filter + """
            GROUP BY
                he.identification_id,
                he.name
            ORDER BY
                he.identification_id,
                he.name
        """
        
        self.env.cr.execute(query, params)
        return self.env.cr.dictfetchall()