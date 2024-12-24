from odoo import api, models, fields
from datetime import datetime

class TabunganPTU(models.Model):
    _name = 'tabungan.ptu'
    _description = 'Tabungan PTU'
    _rec_name = 'kode'

    kode = fields.Char(string="Kode")
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    tanggal = fields.Datetime(string="Tanggal", default=fields.Datetime.now())
    karyawan = fields.Many2one('hr.employee', string="Karyawan")
    saldo = fields.Float(string="Saldo", compute="compute_saldo_tabungan")
    nominal_ptu = fields.Float(string="Nominal PTU")
    keterangan = fields.Text(string="Keterangan")       

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

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('identification_id', operator, name)]
        employees = self.search(domain + args, limit=limit)
        return employees.name_get()
    state = fields.Selection([
        ('draft', "Draft"),
        ('paid', "Paid"),
        ('edit', "Editing"),
    ], default='draft', string="State")

    @api.depends('karyawan')
    def compute_saldo_tabungan(self):
        """Compute total saldo for employee"""
        for record in self:
            if record.karyawan:
                total_saldo = 0.0
                tabungan_records = self.env['hr.employee.ptu_line'].search([
                    ('employee_id', '=', record.karyawan.id)
                ])
                
                for tabungan in tabungan_records:
                    if tabungan.tipe == 'pengeluaran':
                        total_saldo -= tabungan.nominal
                    elif tabungan.tipe == 'pemasukan':
                        total_saldo += tabungan.nominal
                
                record.saldo = total_saldo
            else:
                record.saldo = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        records = super(TabunganPTU, self).create(vals_list)
        for record in records:
            record.kode = self.env['ir.sequence'].next_by_code('tabungan.ptu.sequence') or 'New'
        return records

    def create_ptu(self):
        for record in self:
            self.env['hr.employee.ptu_line'].create({
                'employee_id': record.karyawan.id,
                'tipe': 'pemasukan',
                'nominal': record.nominal_ptu,
                'state': 'diproses',
                'reference_code': record.kode,  # Use record here
            })

        account_settings = self.env['konfigurasi.komisi'].search([('company_id', '=', self.env.company.id)])
        
        karyawan_name = record.karyawan.name
        karyawan_id = record.karyawan.identification_id or 'Unknown ID'


        journal_entry_tabungan_ptu = self.env['account.move'].sudo().create({
            'company_id': self.company_id.id,
            'move_type': 'entry',
            'date': self.tanggal,
            'ref': str(self.keterangan),
            'journal_id': account_settings.journal_kas_1.id,
            'line_ids': [
                (0, 0, {
                    'name': f"{self.kode} - ({karyawan_id})",
                    'date': self.tanggal,
                    'account_id': account_settings.account_kas_1.id,
                    'company_id': self.company_id.id,
                    'debit': self.nominal_ptu,
                }),

                (0, 0, {
                    'name': f"{self.kode} - ({karyawan_id})",
                    'date': self.tanggal,
                    'account_id': account_settings.piutang_komisi.id,
                    'company_id': self.company_id.id,
                    'credit': self.nominal_ptu,
                }),
            ],
        })
        journal_entry_tabungan_ptu.action_post()

        self.state = 'paid'

    def action_edit(self):
        """Enable editing mode for the record"""
        self.ensure_one()
        if self.state == 'paid':
            # Store original values in context for later comparison
            self.write({
                'state': 'edit',
            })
        return True

    def action_save_edit(self):
        """Save changes and update all related records"""
        self.ensure_one()
        if self.state == 'edit':
            karyawan_name = self.karyawan.name
            karyawan_id = self.karyawan.identification_id or 'Unknown ID'
            # Find the original PTU line entry
            original_ptu_line = self.env['hr.employee.ptu_line'].search([
                ('employee_id', '=', self.karyawan.id),
                ('reference_code', '=', self.kode),
                ('tipe', '=', 'pemasukan')
            ], limit=1)

            if original_ptu_line:
                old_nominal = original_ptu_line.nominal
                difference = self.nominal_ptu - old_nominal

                if difference != 0:
                    # Update the original PTU line
                    original_ptu_line.write({
                        'nominal': self.nominal_ptu
                    })

                    # Create adjustment journal entry
                    account_settings = self.env['konfigurasi.komisi'].search([
                        ('company_id', '=', self.env.company.id)
                    ], limit=1)

                    if account_settings:
                        # Reverse the original journal entry
                        original_move = self.env['account.move'].search([
                            ('ref', 'like', self.keterangan),
                            ('line_ids.name', '=', f"{self.kode} - ({karyawan_id})")
                        ], limit=1)

                        if original_move:
                            # Create new journal entry with updated amount
                            new_journal_entry = self.env['account.move'].sudo().create({
                                'company_id': self.company_id.id,
                                'move_type': 'entry',
                                'date': datetime.now(),
                                'ref': f"{self.keterangan} (Edited)",
                                'journal_id': account_settings.journal_kas_1.id,
                                'line_ids': [
                                    (0, 0, {
                                        'name': f"{self.kode} - ({karyawan_id})",
                                        'date': datetime.now(),
                                        'account_id': account_settings.account_kas_1.id,
                                        'company_id': self.company_id.id,
                                        'debit': self.nominal_ptu,
                                    }),
                                    (0, 0, {
                                        'name': f"{self.kode} - ({karyawan_id})",
                                        'date': datetime.now(),
                                        'account_id': account_settings.piutang_komisi.id,
                                        'company_id': self.company_id.id,
                                        'credit': self.nominal_ptu,
                                    }),
                                ],
                            })
                            
                            # Post the new journal entry
                            new_journal_entry.action_post()
                            
                            # Create reverse entry for old amount
                            reverse_entry = self.env['account.move'].sudo().create({
                                'company_id': self.company_id.id,
                                'move_type': 'entry',
                                'date': datetime.now(),
                                'ref': f"Reverse entry for {self.kode}",
                                'journal_id': account_settings.journal_kas_1.id,
                                'line_ids': [
                                    (0, 0, {
                                        'name': f"{self.kode} (Reverse)",
                                        'date': datetime.now(),
                                        'account_id': account_settings.account_kas_1.id,
                                        'company_id': self.company_id.id,
                                        'credit': old_nominal,
                                    }),
                                    (0, 0, {
                                        'name': f"{self.kode} (Reverse)",
                                        'date': datetime.now(),
                                        'account_id': account_settings.piutang_komisi.id,
                                        'company_id': self.company_id.id,
                                        'debit': old_nominal,
                                    }),
                                ],
                            })
                            
                            # Post the reverse entry
                            reverse_entry.action_post()

            # Trigger saldo recomputation
            self._recompute_saldo()
            
            # Update state
            self.write({
                'state': 'paid'
            })
            
        return True

    def action_cancel_edit(self):
        """Cancel editing mode and revert changes"""
        self.ensure_one()
        if self.state == 'edit':
            # Find and revert to original values
            original_ptu_line = self.env['hr.employee.ptu_line'].search([
                ('employee_id', '=', self.karyawan.id),
                ('reference_code', '=', self.kode),
                ('tipe', '=', 'pemasukan')
            ], limit=1)

            if original_ptu_line:
                self.nominal_ptu = original_ptu_line.nominal

            self.state = 'paid'
        return True

    def _recompute_saldo(self):
        """Force recomputation of saldo"""
        self.ensure_one()
        self.invalidate_cache(fnames=['saldo'])
        self.compute_saldo_tabungan()