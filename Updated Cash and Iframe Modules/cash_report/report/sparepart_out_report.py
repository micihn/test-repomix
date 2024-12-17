from odoo import models, api

class SparepartOutReport(models.AbstractModel):
    _name = 'report.cash_report.sparepart_out_template'
    _description = 'Sparepart Out Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data:
            data = {}

        wizard = self.env['sparepart.out.wizard'].browse(docids)
        report_data = wizard.get_sparepart_out_data(data)

        return {
            'doc_ids': docids,
            'doc_model': 'sparepart.out.wizard',
            'docs': wizard,
            'data': data,
            'report_data': report_data or [],
        }