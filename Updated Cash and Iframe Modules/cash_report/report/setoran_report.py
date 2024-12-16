from odoo import models, api

class SetoranReport(models.AbstractModel):
    _name = 'report.cash_report.setoran_report_template'
    _description = 'Setoran Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data:
            data = {}
        
        wizard = self.env['setoran.report.wizard'].browse(docids)
        report_data = wizard.get_setoran_data(data)
        
        return {
            'doc_ids': docids,
            'doc_model': 'setoran.report.wizard',
            'docs': wizard,
            'data': data,
            'report_data': report_data,
            'company': self.env['res.company'].browse(data.get('company_id')),
        }