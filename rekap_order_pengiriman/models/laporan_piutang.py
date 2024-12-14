from odoo import api, models, fields, exceptions
from datetime import date, datetime

class LaporanPiutang(models.TransientModel):
    _name = 'laporan.piutang'
    _description = 'Laporan Piutang ver 2'

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    date_start = fields.Date(string='Tanggal Awal', required=True, default=fields.Date.context_today)
    date_end = fields.Date(string='Tanggal Akhir', required=True, default=fields.Date.context_today)
    all_customer = fields.Boolean(string='Semua Customer', default=True)
    customer_ids = fields.Many2many('res.partner', string='Customer')
    
    filter_unpaid = fields.Boolean(string='Belum Lunas / Partial')
    filter_paid = fields.Boolean(string='Sudah Lunas')
    filter_not_rekap = fields.Boolean(string='Belum Masuk Rekap')

    @api.onchange('all_customer')
    def _onchange_all_customer(self):
        if self.all_customer:
            self.customer_ids = False

    def get_report_data(self):
        if not (self.filter_unpaid or self.filter_paid):
            return {}  # Return empty if no payment status filter selected

        domain = [
            ('create_date', '>=', self.date_start),
            ('create_date', '<=', self.date_end),
            ('company_id', '=', self.company_id.id)
        ]

        if not self.all_customer:
            domain.append(('customer_id', 'in', self.customer_ids.ids))

        rekap_orders = self.env['rekap.order'].search(domain)
        result = {}

        for rekap in rekap_orders:
            customer_key = rekap.customer_id.id
            show_rekap = False
            sudah_rekap_total = sum(line.subtotal_ongkos for line in rekap.sudah_rekap_ids)
            total_bayar = 0.0

            # Check payment status for each invoice in sudah_rekap
            for line in rekap.sudah_rekap_ids:
                for invoice in line.faktur:
                    payment_amount = invoice.amount_total - invoice.amount_residual
                    if self.filter_unpaid and invoice.payment_state in ['not_paid', 'partial']:
                        show_rekap = True
                        total_bayar += payment_amount
                    elif self.filter_paid and invoice.payment_state == 'paid':
                        show_rekap = True
                        total_bayar += payment_amount

            saldo = sudah_rekap_total - total_bayar
            
            if show_rekap:
                if customer_key not in result:
                    result[customer_key] = {
                        'customer': rekap.customer_id,
                        'orders': [],
                        'total_saldo': 0.0,
                        'total_belum_rekap': 0.0
                    }

                result[customer_key]['orders'].append({
                    'kode': rekap.kode_rekap,
                    'tanggal': rekap.create_date,
                    'jumlah': sudah_rekap_total,
                    'bayar': total_bayar,
                    'saldo': saldo
                })
                result[customer_key]['total_saldo'] += saldo

                # Add belum_rekap total if filter is active
                if self.filter_not_rekap:
                    belum_rekap_total = sum(line.subtotal_ongkos for line in rekap.belum_rekap_ids)
                    result[customer_key]['total_belum_rekap'] += belum_rekap_total

        return result

    def print_report(self):
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'date_start': self.date_start,
                'date_end': self.date_end,
                'company_id': self.company_id.id,
                'report_data': self.get_report_data()
            },
        }
        raise exceptions.UserError(str(data))
        return self.env.ref('rekap_order_pengiriman.action_report_laporan_piutang').report_action(self, data=data)