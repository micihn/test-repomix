from odoo import api, models, fields
from odoo.exceptions import UserError
from datetime import date, datetime


class RekapOrder(models.Model):
    _name = 'rekap.order'
    _description = 'Rekap Order Kirim'
    _rec_name = "kode_rekap"

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    kode_rekap = fields.Char(required=True, copy=False)
    keterangan = fields.Text(required=True, copy=False)
    tanggal_awal = fields.Date(required=True, copy=False)
    tanggal_akhir = fields.Date(required=True, copy=False)
    customer_id = fields.Many2one("res.partner", ondelete="restrict", required=True)
    jatuh_tempo = fields.Date(required=True, copy=False)
    tipe_order = fields.Selection([
        ('do', 'DO'),
        ('regular', 'Regular'),
    ], default="do", required=True)
    sudah_rekap_ids = fields.One2many("rekap.order.sudah_rekap", "rekap_id", readonly=False)
    belum_rekap_ids = fields.One2many("rekap.order.belum_rekap", "rekap_id", readonly=False)
    total_sudah_rekap = fields.Float(compute="_compute_total_rekap", store=True)
    total_belum_rekap = fields.Float(compute="_compute_total_rekap", store=True)
    total = fields.Float(compute="_compute_total_rekap", store=True)

    @api.onchange('kode_rekap')
    def _check_kode_rekap(self):
        for i in self:
            if i.kode_rekap:
                rekap = self.env['rekap.order'].search([('kode_rekap', '=', i.kode_rekap)], limit=1)
                if rekap:
                    raise UserError("Kode Rekap sudah digunakan.")

    def populate_item(self):
        for rec in self:
            if rec.tanggal_awal and rec.tanggal_akhir and rec.customer_id and rec.kode_rekap:
                order_ids = self.env['order.pengiriman'].search([
                    ('customer', '=', rec.customer_id.id),
                    ('jenis_order', '=', rec.tipe_order),
                    ('create_date', '>=', datetime.combine(rec.tanggal_awal, datetime.min.time())),
                    ('create_date', '<=', datetime.combine(rec.tanggal_akhir, datetime.max.time())),
                    ('masuk_rekap', '=', False)
                ])
                values = []
                for order in order_ids:
                    setoran_line = self.env['detail.order'].search([('order_pengiriman', '=', order.id)], limit=1)
                    # Check if order_id is already in belum_rekap_ids
                    if setoran_line and setoran_line.order_setoran.state == 'done' and not any(
                            belum_rekap.order_id.id == order.id for belum_rekap in rec.belum_rekap_ids):
                        values.append((0, 0, {
                            'rekap_id': rec.id,
                            'order_id': order.id,
                        }))

                    oper_setoran_line = self.env['detail.order.setoran'].search([('order_pengiriman', '=', order.id)],
                                                                                limit=1)
                    if oper_setoran_line and oper_setoran_line.oper_setoran.state == 'done' and not any(
                            belum_rekap.order_id.id == order.id for belum_rekap in rec.belum_rekap_ids):
                        values.append((0, 0, {
                            'rekap_id': rec.id,
                            'order_id': order.id,
                        }))

                if len(values) > 0:
                    rec.belum_rekap_ids = values
                else:
                    raise UserError("Tidak ada order yang dapat direkap. Pastikan setoran order telah divalidasi.")

    @api.depends("sudah_rekap_ids.subtotal_ongkos", "sudah_rekap_ids.active", "belum_rekap_ids.subtotal_ongkos", "belum_rekap_ids.active")
    def _compute_total_rekap(self):
        for i in self:
            i.total_sudah_rekap = sum([line.subtotal_ongkos for line in i.sudah_rekap_ids]) if len(i.sudah_rekap_ids) > 0 else 0
            i.total_belum_rekap = sum([line.subtotal_ongkos for line in i.belum_rekap_ids]) if len(i.belum_rekap_ids) > 0 else 0
            i.total = i.total_sudah_rekap + i.total_belum_rekap


class RekapOrderItem(models.Model):
    _name = 'rekap.order.item'
    _description = "Order Rekap Line"

    rekap_id = fields.Many2one("rekap.order", ondelete="cascade", required=True, readonly=True)

    company_id = fields.Many2one('res.company', ondelete='cascade', default=lambda self: self.env.user.company_id, readonly=True)
    active = fields.Boolean(default=True, readonly=True)
    order_id = fields.Many2one("order.pengiriman", ondelete="restrict", required=True, readonly=True)

    tanggal = fields.Datetime(related="order_id.create_date", store=True, readonly=True)
    no_surat_jalan = fields.Char(related="order_id.nomor_surat_jalan", store=True, readonly=True)
    plant = fields.Many2one("konfigurasi.plant", related="order_id.plant", store=True, readonly=True)
    faktur = fields.Many2many("account.move", compute="_get_invoice", store=True, readonly=True)
    nomor_kendaraan = fields.Char(compute="set_nomor_kendaraan", readonly=True)
    alamat_muat = fields.Many2one("konfigurasi.lokasi", related="order_id.alamat_muat", store=True, readonly=True)
    alamat_bongkar = fields.Many2one("konfigurasi.lokasi", related="order_id.alamat_bongkar", store=True, readonly=True)
    detail_alamat_bongkar = fields.Text('Detail Alamat Bongkar', related="order_id.detail_alamat_bongkar", store=True, readonly=True)

    nama_barang = fields.Text(compute="_get_item_data", store=True, readonly=True)
    jumlah_per_kg_do = fields.Float(related="order_id.detail_order_do.jumlah_per_kg", store=True, readonly=True)
    subtotal_ongkos = fields.Float(compute="_compute_subtotal_ongkos", store=True, readonly=False)  # Change store=True to readonly=False

    # Add new fields for Regular orders
    panjang_barang = fields.Float(compute="_get_item_data", store=True, readonly=True)
    lebar_barang = fields.Float(compute="_get_item_data", store=True, readonly=True)
    tinggi_barang = fields.Float(compute="_get_item_data", store=True, readonly=True)
    isi = fields.Float(compute="_compute_isi", store=True, readonly=True)

    nominal_revisi = fields.Float(string="Nominal Revisi")

    @api.depends('nominal_revisi')
    def _compute_subtotal_ongkos(self):
        for record in self:
            if record.nominal_revisi:  # If nominal_revisi is not null or greater than 0
                record.subtotal_ongkos = record.nominal_revisi
            else:
                # You can put the logic here to get the original subtotal_ongkos if needed
                record.subtotal_ongkos = 0  # Or set it to another default value if necessary

    # ... (rest of your existing methods)


    def find_master_jasa_pengiriman(self):
        # Mengambil ID Database Produk berdasarkan external ID
        external_id = self.env.ref('order_setoran.product_jasa_pengiriman')
        product_id = self.env['product.product'].search([('product_tmpl_id', '=', int(external_id))]).id
        return product_id

    def validate_revision(self):
        for record in self:
            if record.nominal_revisi > 0:
                for invoice in record.faktur:

                    reverse_wizard = self.env['account.move.reversal'].sudo().create({
                        'date': fields.Date.today(),
                        'reason': 'Revisi Nominal',
                        'refund_method': 'cancel',
                        'journal_id': invoice.journal_id.id,
                        'move_ids': [(6, 0, [invoice.id])],
                    })

                    # Validate and apply the reversal
                    reverse_wizard.reverse_moves()

                    product_id = self.find_master_jasa_pengiriman()
                    new_invoice = self.env['account.move'].sudo().create({
                        'company_id': self.env.company.id,
                        'move_type': 'out_invoice',
                        'invoice_date': fields.Date.today(),
                        'date': fields.Date.today(),
                        'partner_id': invoice.partner_id.id,
                        'currency_id': self.env.user.company_id.currency_id.id,
                        'invoice_origin': invoice.ref,
                        'invoice_line_ids': [
                            (0, 0, {
                                'product_id' : product_id,
                                'name': 'Jasa Pengiriman',
                                'price_unit': record.nominal_revisi,
                                'tax_ids': None,
                            })
                        ],
                    })

                    new_invoice.action_post()

                    record.write({
                        'faktur': [(4, invoice.id), (4, new_invoice.id)]
                    })

    @api.depends('order_id')
    def set_nomor_kendaraan(self):
        for record in self:
            if record.order_id.nomor_setoran:
                record.nomor_kendaraan = record.order_id.kendaraan.display_name
            elif record.order_id.oper_setoran:
                record.nomor_kendaraan = self.env['oper.setoran'].search([('id', '=', record.order_id.oper_setoran)]).kendaraan
            else:
                record.nomor_kendaraan = False

    @api.depends("order_id")
    def _get_item_data(self):
        for i in self:
            if i.order_id:
                if i.order_id.jenis_order == 'do':
                    i.nama_barang = "\n".join([line.nama_barang for line in i.order_id.detail_order_do])
                    i.panjang_barang = 0.0
                    i.lebar_barang = 0.0
                    i.tinggi_barang = 0.0
                else:
                    i.nama_barang = "\n".join([line.nama_barang for line in i.order_id.detail_order_reguler])
                    # Get dimensions from the first detail_order_reguler line
                    if i.order_id.detail_order_reguler:
                        first_line = i.order_id.detail_order_reguler[0]
                        i.panjang_barang = first_line.panjang_barang
                        i.lebar_barang = first_line.lebar_barang
                        i.tinggi_barang = first_line.tinggi_barang
                    else:
                        i.panjang_barang = 0.0
                        i.lebar_barang = 0.0
                        i.tinggi_barang = 0.0
                i.subtotal_ongkos = i.order_id.total_ongkos
            else:
                i.nama_barang = ""
                i.subtotal_ongkos = 0
                i.panjang_barang = 0.0
                i.lebar_barang = 0.0
                i.tinggi_barang = 0.0

    @api.depends('panjang_barang', 'lebar_barang', 'tinggi_barang')
    def _compute_isi(self):
        for record in self:
            record.isi = record.panjang_barang * record.lebar_barang * record.tinggi_barang

    @api.depends("order_id")
    def _get_invoice(self):
        for i in self:
            if i.order_id:
                detail_orders = self.env['detail.order'].sudo().search([('order_pengiriman', '=', i.order_id.id)])
                invoice_ids = []
                for detail_order in detail_orders:
                    invoices = self.env['account.move'].sudo().search([
                        ('nomor_setoran', '=', detail_order.order_setoran.kode_order_setoran),
                        ('invoice_origin', '=', detail_order.order_pengiriman.order_pengiriman_name),
                        ('move_type', '=', 'out_invoice')
                    ])
                    invoice_ids.extend(invoices.ids)

                oper_setoran_line = self.env['detail.order.setoran'].search([('order_pengiriman', '=', i.order_id.id)])
                for detail_order in oper_setoran_line:
                    invoices = self.env['account.move'].sudo().search([
                        ('nomor_setoran', '=', detail_order.oper_setoran.kode_oper_setoran),
                        ('invoice_origin', '=', detail_order.order_pengiriman.order_pengiriman_name),
                        ('move_type', '=', 'out_invoice')
                    ])
                    invoice_ids.extend(invoices.ids)

                i.faktur = [(6, 0, invoice_ids)] if invoice_ids else [(5, 0, 0)]
            else:
                i.faktur = [(5, 0, 0)]


class RekapOrderSudah(models.Model):
    _name = 'rekap.order.sudah_rekap'
    _inherit = "rekap.order.item"
    _description = "Order Rekap Sudah Rekap"

    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    inverse_id = fields.Many2one("rekap.order.belum_rekap", ondelete="cascade", readonly=True)


    def toggle_state(self):
        for i in self:
            for invoice in i.faktur:
                if invoice.state == 'posted':
                    raise UserError(
                        "Tidak dapat mengembalikan rekapan order ini. Order memiliki invoice yang sudah dibayar.")

            if not i.inverse_id:
                i.inverse_id = self.env['rekap.order.belum_rekap'].create({
                    'rekap_id': i.rekap_id.id,
                    'order_id': i.order_id.id,
                    'inverse_id': i.id,
                })
            else:
                i.inverse_id.active = True

            belum_rekap_ids = self.env['rekap.order.belum_rekap'].with_context({'active_test': False}).search(
                [('order_id', '=', i.order_id.id), ('id', '!=', i.inverse_id.id)])
            for belum_rekap in belum_rekap_ids:
                belum_rekap.active = True

            i.order_id.masuk_rekap = False
            i.active = False


class RekapOrderBelum(models.Model):
    _name = 'rekap.order.belum_rekap'
    _inherit = "rekap.order.item"
    _description = "Order Rekap Belum"

    inverse_id = fields.Many2one("rekap.order.sudah_rekap", ondelete="cascade", readonly=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)

    def toggle_state(self):
        for i in self:
            if not i.inverse_id:
                i.inverse_id = self.env['rekap.order.sudah_rekap'].create({
                    'rekap_id': i.rekap_id.id,
                    'order_id': i.order_id.id,
                    'inverse_id': i.id,
                })
            else:
                i.inverse_id.active = True

            belum_rekap_ids = self.env['rekap.order.belum_rekap'].search(
                [('order_id', '=', i.order_id.id), ('id', '!=', i.id)])
            for belum_rekap in belum_rekap_ids:
                belum_rekap.active = False

            i.order_id.masuk_rekap = True
            i.active = False