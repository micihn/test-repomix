from odoo import models, api

class SetoranLangsungReport(models.AbstractModel):
    _name = 'report.cash_report.setoran_langsung_template'
    _description = 'Setoran Langsung Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data:
            data = {}

        wizard = self.env['setoran.langsung.wizard'].browse(docids)
        report_data = wizard.get_setoran_langsung_data(data)

        return {
            'doc_ids': docids,
            'doc_model': 'setoran.langsung.wizard',
            'docs': wizard,
            'data': data,
            'report_data': report_data,
            'company': self.env['res.company'].browse(data.get('company_id')),
        }