from odoo import models, api

class SparepartReturnReport(models.AbstractModel):
    _name = 'report.cash_report.sparepart_return_template'
    _description = 'Sparepart Return Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data:
            data = {}

        wizard = self.env['sparepart.return.wizard'].browse(docids)
        report_data = wizard.get_sparepart_return_data(data)

        return {
            'doc_ids': docids,
            'doc_model': 'sparepart.return.wizard',
            'docs': wizard,
            'data': data,
            'report_data': report_data,
        }