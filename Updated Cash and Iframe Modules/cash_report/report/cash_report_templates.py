from odoo import models, api

class CashReportPDF(models.AbstractModel):
    _name = 'report.cash_report.cash_report_template'
    _description = 'Cash Report PDF Template'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data:
            data = {}
            
        report_data = self.env['cash.report'].get_cash_report_data(data)
        account = self.env['account.account'].browse(data.get('account_id'))
        
        return {
            'doc_ids': docids,
            'doc_model': 'cash.report.wizard',
            'docs': self.env['cash.report.wizard'].browse(docids),
            'data': data,
            'report_data': report_data,
            'company': self.env['res.company'].browse(data.get('company_id')),
            'account': account,
        }