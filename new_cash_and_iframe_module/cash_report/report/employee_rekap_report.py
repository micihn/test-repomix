from odoo import models, api

class EmployeeRekapReport(models.AbstractModel):
    _name = 'report.cash_report.employee_rekap_template'
    _description = 'Employee Rekap Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data:
            data = {}

        wizard = self.env['employee.rekap.wizard'].browse(docids)
        report_data = wizard.get_employee_rekap_data(data)

        return {
            'doc_ids': docids,
            'doc_model': 'employee.rekap.wizard',
            'docs': wizard,
            'data': data,
            'report_data': report_data,
        }