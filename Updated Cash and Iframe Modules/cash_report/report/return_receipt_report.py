from odoo import models, api

class ReturnReceiptReport(models.AbstractModel):
    _name = 'report.cash_report.return_receipt_template'
    _description = 'Return Receipt Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data:
            data = {}

        wizard = self.env['return.receipt.wizard'].browse(docids)
        report_data = wizard.get_return_data(data)

        return {
            'doc_ids': docids,
            'doc_model': 'return.receipt.wizard',
            'docs': wizard,
            'data': data,
            'report_data': report_data or [],  # Ensure we always have a list, even if empty
        }