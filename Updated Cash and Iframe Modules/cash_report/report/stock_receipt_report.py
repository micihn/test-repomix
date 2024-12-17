from odoo import models, api

class StockReceiptReport(models.AbstractModel):
    _name = 'report.cash_report.stock_receipt_template'
    _description = 'Stock Receipt Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data:
            data = {}

        wizard = self.env['stock.receipt.wizard'].browse(docids)
        report_data = wizard.get_receipt_data(data)

        return {
            'doc_ids': docids,
            'doc_model': 'stock.receipt.wizard',
            'docs': wizard,
            'data': data,
            'report_data': report_data,
        }