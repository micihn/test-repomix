from odoo import api, models, fields, exceptions, _
from datetime import date, datetime
import logging
_logger = logging.getLogger(__name__)

class LaporanRekapWizard(models.TransientModel):
	_name = "laporan.rekap.wiz"
	_description = "Wizard Laporan Rekap"

	company_id = fields.Many2one("res.company", ondelete="set null", string="Company", default=lambda self: self.env.company)
	start_date = fields.Date(string="Tanggal Awal", required=True)
	end_date = fields.Date(string="Tanggal Akhir", required=True)
	all_customer = fields.Boolean(string="Semua Customer")
	customer_ids = fields.Many2many("res.partner", string="Customer", domain="[('company_id', '=', company_id)]")
	unpaid = fields.Boolean(string="Belum Lunas / Partial")
	paid = fields.Boolean(string="Sudah Lunas")
	no_summary = fields.Boolean(string="Belum Rekap")

	@api.constrains("start_date", "end_date")
	def _validate_dates(self):
		for wiz in self:
			if wiz.end_date <= wiz.start_date:
				raise exceptions.UserError("Tanggal akhir harus melebihi tanggal awal.")

	def print_report(self):
		for wiz in self:
			data = {
				'ids': wiz.ids,
				'model': wiz._name,
				'company_id': wiz.company_id.id,
				'start_date': wiz.start_date,
				'end_date': wiz.end_date,
				'all_customer': wiz.all_customer,
				'customer_ids': wiz.customer_ids.ids,
				'unpaid': wiz.unpaid,
				'paid': wiz.paid,
				'no_summary': wiz.no_summary,
			}
			return self.env.ref('rekap_order_pengiriman.laporan_rekap_piutang_report').report_action(self, data=data)


class ReportAttendanceRecap(models.AbstractModel):
	_name = 'report.rekap_order_pengiriman.laporan_rekap_piutang_template'

	@api.model
	def _get_report_values(self, docids, data=None):
		company_id = self.env['res.company'].browse(data['company_id'])
		start_date = data['start_date']
		end_date = data['end_date']
		all_customer = data['all_customer']
		customer_ids = []
		if all_customer:
			rekap = self.env['rekap.order'].sudo().search([('company_id', '=', company_id.id)])
			customer_ids = [rec.customer_id for rec in rekap]
		else:
			customer_ids = self.env['res.partner'].browse(data['customer_ids'])
		# customer_ids = self.env['res.partner'].browse(data['customer_ids']) if not all_customer else self.env['res.partner'].search([('company_id', '=', company_id.id), ('customer_rank', '!=', 0)])
		unpaid = data['unpaid']
		paid = data['paid']
		no_summary = data['no_summary']

		REKAP_DOMAIN = [('tanggal', '>=', start_date), ('tanggal', '<=', end_date), ('active', '=', True)]
		# INVOICE_DOMAIN = []
		# if unpaid:
		# 	INVOICE_DOMAIN += [('amount_residual', '>', 0)]

		docs = []
		for customer in customer_ids:
			active_doc = next((item for item in docs if item['customer_id'] == customer), False)
			if not active_doc: # Declare dictionary if not found
				docs.append({
					'customer_id': customer,
					'line': [],
					'total_unpaid': 0,
					'total_not_listed': 0,
					'total_down_payment': 0,
				})
				active_doc = next((item for item in docs if item['customer_id'] == customer), False)
			INVOICE_DOMAIN = [('partner_id', '=', customer.id), ('move_type', '=', 'out_invoice'), ('invoice_date', '>=', start_date), ('invoice_date', '<=', end_date)]
			PAYMENT_STATE = [('payment_state', 'in', [])]
			# Filters
			if unpaid:
				PAYMENT_STATE[0][2].append('not_paid')
				PAYMENT_STATE[0][2].append('partial')
				PAYMENT_STATE[0][2].append('in_payment')

			if paid:
				PAYMENT_STATE[0][2].append('paid')

			if paid or unpaid:
				INVOICE_DOMAIN += PAYMENT_STATE

			invoices = self.env['account.move'].search(INVOICE_DOMAIN)

			for invoice in invoices:
				sudah_rekap = self.env['rekap.order.sudah_rekap'].search(REKAP_DOMAIN + [('faktur', 'in', [invoice.id]), ('rekap_id.customer_id', '=', customer.id)], limit=1)
				belum_rekap = self.env['rekap.order.belum_rekap'].search(REKAP_DOMAIN + [('faktur', 'in', [invoice.id]), ('rekap_id.customer_id', '=', customer.id)], limit=1)
				rekap_date = False
				if sudah_rekap and not belum_rekap:
					rekap_date = sudah_rekap.tanggal
				if belum_rekap and not sudah_rekap:
					rekap_date = belum_rekap.tanggal

				paid, unpaid = invoice.amount_total - invoice.amount_residual, invoice.amount_residual

				# Filters
				if not no_summary: # Sudah masuk rekap (invoice & sudah_rekap)
					if sudah_rekap:
						active_doc['line'].append({
							'invoice_id': invoice,
							'rekap_date': rekap_date.strftime('%d/%m/%Y') if rekap_date else rekap_date,
							'amount_total': invoice.amount_total,
							'amount_paid': paid,
							'amount_unpaid': unpaid,
						})
				else: # Belum buat rekap (invoice only)
					if not sudah_rekap and not belum_rekap:
						active_doc['line'].append({
							'invoice_id': invoice,
							'rekap_date': False,
							'amount_total': invoice.amount_total,
							'amount_paid': paid,
							'amount_unpaid': unpaid,
						})
				active_doc['total_unpaid'] += unpaid
				active_doc['total_not_listed'] += invoice.amount_total if not sudah_rekap and not belum_rekap else 0

		return {
			'doc_ids': data['ids'],
			'doc_model': data['model'],
			'docs': docs,
			'company_id': company_id,
			'start_date': datetime.strptime(start_date, "%Y-%m-%d"),
			'end_date': datetime.strptime(end_date, "%Y-%m-%d"),
		}