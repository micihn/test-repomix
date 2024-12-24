from odoo import api, models, fields
from odoo.exceptions import ValidationError
from datetime import datetime

class BayarKomisi(models.Model):
    _name = "bayar.komisi"
    _description = "Pembayaran Komisi"
    _rec_name = "kode_pembayaran"

    kode_pembayaran = fields.Char(readonly=True)
    employee_id = fields.Many2one("hr.employee", ondelete="cascade", required=True, states={
        'selesai': [('readonly', True)],
        'dibayar': [('readonly', True)],
        'edit': [('readonly', True)]
    })
    saldo = fields.Float(related="employee_id.komisi_tertabung", readonly=True)
    jumlah = fields.Float(required=True, states={
        'selesai': [('readonly', True)],
        'dibayar': [('readonly', True)]
    })
    keterangan = fields.Text(states={
        'selesai': [('readonly', True)],
        'dibayar': [('readonly', True)]
    })
    ptu_line_id = fields.Many2one("hr.employee.ptu_line", ondelete="set null", readonly=True)
    account_move_id = fields.Many2one("account.move", ondelete="set null", readonly=True)
    state = fields.Selection([
        ('dibuat', 'Dibuat'),
        ('selesai', 'Selesai'),
        ('dibayar', 'Dibayar'),
        ('edit', 'Editing'),
    ], default="dibuat")
    company_id = fields.Many2one("res.company", ondelete="cascade",
                                default=lambda self: self.env.context['allowed_company_ids'][0])

    @api.model
    def create(self, vals_list):
        records = super(BayarKomisi, self).create(vals_list)
        for rec in records:
            rec.kode_pembayaran = self.env['ir.sequence'].next_by_code('bayar.komisi') or 'New'
        return records

    def action_submit(self):
        for rec in self:
            rec.state = 'dibayar'

            if not rec.ptu_line_id:
                rec.ptu_line_id = self.env['hr.employee.ptu_line'].create({
                    'employee_id': rec.employee_id.id,
                    'nominal': rec.jumlah,
                    'tipe': 'pengeluaran',
                    'state': 'pending',
                    'reference_code': rec.kode_pembayaran,
                }).id

            if not rec.account_move_id:
                account_settings = self.env['konfigurasi.komisi'].search([('company_id', '=', self.env.company.id)])
                journal_kas_1 = account_settings.journal_kas_1
                journal_kas_2 = account_settings.journal_kas_2
                account_kas_1 = account_settings.account_kas_1
                account_kas_2 = account_settings.account_kas_2
                hutang_komisi = account_settings.hutang_komisi
                piutang_komisi = account_settings.piutang_komisi
                expense_komisi = account_settings.expense_komisi

                if not journal_kas_1 or not journal_kas_2 or not account_kas_1 or not account_kas_2 or not hutang_komisi or not piutang_komisi or not expense_komisi:
                    raise ValidationError("Anda belum melakukan konfigurasi account pada menu Komisi > Konfigurasi.")

                journal_entry_bayar_komisi = self.env['account.move'].sudo().create({
                    'company_id': self.env.company.id,
                    'move_type': 'entry',
                    'date': fields.Datetime.now(),
                    'journal_id': journal_kas_2.id,
                    'ref': str(self.kode_pembayaran),
                    'line_ids': [
                        (0, 0, {
                            'name': self.kode_pembayaran,
                            'date': fields.Datetime.now(),
                            'account_id': hutang_komisi.id,
                            'company_id': self.env.company.id,
                            'debit': rec.jumlah,
                        }),
                        (0, 0, {
                            'name': self.kode_pembayaran,
                            'date': fields.Datetime.now(),
                            'account_id': account_kas_1.id,
                            'company_id': self.env.company.id,
                            'credit': rec.jumlah,
                        }),
                    ],
                })
                journal_entry_bayar_komisi.action_post()

    def action_edit(self):
        """Enable editing mode for the record"""
        self.ensure_one()
        if self.state == 'dibayar':
            self.write({
                'state': 'edit',
            })
        return True

    def action_save_edit(self):
        """Save changes and update all related records"""
        self.ensure_one()
        if self.state == 'edit':
            # Find the original PTU line entry
            original_ptu_line = self.env['hr.employee.ptu_line'].search([
                ('employee_id', '=', self.employee_id.id),
                ('reference_code', '=', self.kode_pembayaran),
                ('tipe', '=', 'pengeluaran')
            ], limit=1)

            if original_ptu_line:
                old_jumlah = original_ptu_line.nominal
                difference = self.jumlah - old_jumlah

                if difference != 0:
                    # Update the original PTU line
                    original_ptu_line.write({
                        'nominal': self.jumlah
                    })

                    # Create adjustment journal entries
                    account_settings = self.env['konfigurasi.komisi'].search([
                        ('company_id', '=', self.env.company.id)
                    ], limit=1)

                    if account_settings:
                        # Create new journal entry with updated amount
                        new_journal_entry = self.env['account.move'].sudo().create({
                            'company_id': self.company_id.id,
                            'move_type': 'entry',
                            'date': datetime.now(),
                            'ref': f"{self.kode_pembayaran} (Edited)",
                            'journal_id': account_settings.journal_kas_2.id,
                            'line_ids': [
                                (0, 0, {
                                    'name': f"{self.kode_pembayaran} (Updated)",
                                    'date': datetime.now(),
                                    'account_id': account_settings.hutang_komisi.id,
                                    'company_id': self.company_id.id,
                                    'debit': self.jumlah,
                                }),
                                (0, 0, {
                                    'name': f"{self.kode_pembayaran} (Updated)",
                                    'date': datetime.now(),
                                    'account_id': account_settings.account_kas_1.id,
                                    'company_id': self.company_id.id,
                                    'credit': self.jumlah,
                                }),
                            ],
                        })
                        new_journal_entry.action_post()

                        # Create reverse entry for old amount
                        reverse_entry = self.env['account.move'].sudo().create({
                            'company_id': self.company_id.id,
                            'move_type': 'entry',
                            'date': datetime.now(),
                            'ref': f"Reverse entry for {self.kode_pembayaran}",
                            'journal_id': account_settings.journal_kas_2.id,
                            'line_ids': [
                                (0, 0, {
                                    'name': f"{self.kode_pembayaran} (Reverse)",
                                    'date': datetime.now(),
                                    'account_id': account_settings.hutang_komisi.id,
                                    'company_id': self.company_id.id,
                                    'credit': old_jumlah,
                                }),
                                (0, 0, {
                                    'name': f"{self.kode_pembayaran} (Reverse)",
                                    'date': datetime.now(),
                                    'account_id': account_settings.account_kas_1.id,
                                    'company_id': self.company_id.id,
                                    'debit': old_jumlah,
                                }),
                            ],
                        })
                        reverse_entry.action_post()

            self.write({
                'state': 'dibayar'
            })

        return True

    def action_cancel_edit(self):
        """Cancel editing mode and revert changes"""
        self.ensure_one()
        if self.state == 'edit':
            # Find and revert to original values
            original_ptu_line = self.env['hr.employee.ptu_line'].search([
                ('employee_id', '=', self.employee_id.id),
                ('reference_code', '=', self.kode_pembayaran),
                ('tipe', '=', 'pengeluaran')
            ], limit=1)

            if original_ptu_line:
                self.jumlah = original_ptu_line.nominal

            self.write({
                'state': 'dibayar'
            })
        return True

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('identification_id', operator, name)]
        employees = self.search(domain + args, limit=limit)
        return employees.name_get()
