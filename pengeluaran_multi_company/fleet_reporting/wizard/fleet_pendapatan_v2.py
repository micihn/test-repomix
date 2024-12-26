from odoo import api, fields, models
from datetime import datetime

class FleetPendapatanV2(models.TransientModel):
    _name = 'fleet.pendapatan.v2'
    _description = 'Pendapatan Truk V2 Wizard'

    # Fleet Selection - updated with relation table name
    fleet_ids = fields.Many2many(
        'fleet.vehicle', 
        'fleet_pendapatan_v2_vehicle_rel',  # Specific relation table name
        'wizard_id',
        'vehicle_id',
        string='Nomor Truk'
    )
    all_fleet = fields.Boolean('Semua Truk')
    
    # Model Year Selection
    model_year = fields.Selection(
        selection='_get_model_years',
        string='Tahun Rakit'
    )
    all_years = fields.Boolean('Semua Tahun')
    
    # Vehicle Type Selection
    vehicle_type_id = fields.Many2one('fleet.vehicle.model.category', string='Jenis Truk')
    all_types = fields.Boolean('Semua Jenis')
    
    # Date/Year Filter Selection
    filter_type = fields.Selection([
        ('date_range', 'Range Tanggal'),
        ('year', 'Tahun')
    ], string='Tipe Filter', default='date_range', required=True)
    
    # Date Range Fields
    date_start = fields.Date('Tanggal Awal')
    date_end = fields.Date('Tanggal Akhir')
    
    # Year Field
    year = fields.Integer('Tahun')
    
    # Date Based On
    date_based_on = fields.Selection([
        ('setoran', 'Tanggal Setoran'),
        ('uang_jalan', 'Tanggal Uang Jalan')
    ], string='Berdasarkan', required=True, default='setoran')

    @api.model
    def _get_model_years(self):
        """Get unique model years from fleet vehicles"""
        vehicles = self.env['fleet.vehicle'].search([])
        years = set(vehicle.model_year for vehicle in vehicles if vehicle.model_year)
        return [(str(year), str(year)) for year in sorted(years, reverse=True)]

    @api.onchange('all_fleet')
    def _onchange_all_fleet(self):
        if self.all_fleet:
            self.fleet_ids = [(6, 0, self.env['fleet.vehicle'].search([]).ids)]
        else:
            self.fleet_ids = [(5, 0, 0)]

    @api.onchange('all_years')
    def _onchange_all_years(self):
        if self.all_years:
            self.model_year = False

    @api.onchange('all_types')
    def _onchange_all_types(self):
        if self.all_types:
            self.vehicle_type_id = False

    @api.onchange('filter_type')
    def _onchange_filter_type(self):
        if self.filter_type == 'date_range':
            self.year = False
        else:
            self.date_start = False
            self.date_end = False

    def generate_report(self):
        # Initial domain for vehicles
        domain = [('company_id', '=', self.env.company.id)]  # Add company filter
        if not self.all_fleet:
            if self.fleet_ids:
                domain.append(('id', 'in', self.fleet_ids.ids))
            if not self.all_years and self.model_year:
                domain.append(('model_year', '=', self.model_year))
            if not self.all_types and self.vehicle_type_id:
                domain.append(('model_id.category_id', '=', self.vehicle_type_id.id))
        
        # Get all matching vehicles
        vehicles = self.env['fleet.vehicle'].search(domain)
        
        # Prepare date domain for orders
        order_domain = [
            ('state', '=', 'done'),
            ('company_id', '=', self.env.company.id)  # Add company filter
        ]
        
        if self.filter_type == 'date_range':
            date_field = 'tanggal_st' if self.date_based_on == 'setoran' else 'tanggal_uj'
            order_domain += [
                (date_field, '>=', self.date_start),
                (date_field, '<=', self.date_end),
            ]
        else:  # year filter
            date_field = 'tanggal_st' if self.date_based_on == 'setoran' else 'tanggal_uj'
            order_domain += [
                ('tanggal_st', '>=', f'{self.year}-01-01'),
                ('tanggal_st', '<=', f'{self.year}-12-31'),
            ]

        # Get all orders for the period
        all_orders = self.env['order.setoran'].search(order_domain)
        
        # Get only vehicles that have orders
        vehicles_with_orders = vehicles.filtered(lambda v: v.id in all_orders.mapped('kendaraan').ids)

        # Prepare data structure by category
        categories = {}
        for vehicle in vehicles_with_orders:  # Only process vehicles with orders
            category_name = vehicle.model_id.category_id.name or 'Uncategorized'
            if category_name not in categories:
                categories[category_name] = {
                    'category_name': category_name,
                    'vehicles': [],
                    'total_hasil_jasa': 0,
                    'total_pengeluaran': 0,
                    'total_spare_part': 0,
                    'total_sisa': 0,
                }

            # Get orders for this vehicle
            vehicle_orders = all_orders.filtered(lambda o: o.kendaraan.id == vehicle.id)
            
            # Skip if no orders found
            if not vehicle_orders:
                continue
            
            # Calculate vehicle totals
            hasil_jasa = sum(order.total_jumlah for order in vehicle_orders)
            pengeluaran = sum(order.total_pengeluaran for order in vehicle_orders)
            
            # Get spare parts for this vehicle with company filter
            spare_part_domain = [
                ('vehicle_id', '=', vehicle.id),
                ('state_record', '=', 'selesai'),
                ('service_type_id.category', '=', 'sparepart'),
                ('company_id', '=', self.env.company.id)
            ]
            
            if self.filter_type == 'date_range':
                spare_part_domain += [
                    ('date', '>=', self.date_start),
                    ('date', '<=', self.date_end),
                ]
            else:
                spare_part_domain += [
                    ('date', '>=', f'{self.year}-01-01'),
                    ('date', '<=', f'{self.year}-12-31'),
                ]
            
            spare_parts = self.env['fleet.vehicle.log.services'].search(spare_part_domain)
            spare_part_total = sum(service.amount for service in spare_parts)
            
            # Calculate sisa and percentages
            sisa = hasil_jasa - pengeluaran - spare_part_total
            pengeluaran_percent = (pengeluaran / hasil_jasa * 100) if hasil_jasa else 0
            spare_part_percent = (spare_part_total / hasil_jasa * 100) if hasil_jasa else 0
            sisa_percent = (sisa / hasil_jasa * 100) if hasil_jasa else 0
            
            vehicle_data = {
                'license_plate': vehicle.license_plate,
                'year': vehicle.model_year,
                'hasil_jasa': hasil_jasa,
                'pengeluaran': pengeluaran,
                'pengeluaran_percent': pengeluaran_percent,
                'spare_part': spare_part_total,
                'spare_part_percent': spare_part_percent,
                'sisa': sisa,
                'sisa_percent': sisa_percent,
            }
            
            categories[category_name]['vehicles'].append(vehicle_data)
            categories[category_name]['total_hasil_jasa'] += hasil_jasa
            categories[category_name]['total_pengeluaran'] += pengeluaran
            categories[category_name]['total_spare_part'] += spare_part_total
            categories[category_name]['total_sisa'] += sisa

        # Calculate category totals and percentages
        for category in categories.values():
            if category['total_hasil_jasa']:
                category['total_pengeluaran_percent'] = (category['total_pengeluaran'] / category['total_hasil_jasa'] * 100)
                category['total_spare_part_percent'] = (category['total_spare_part'] / category['total_hasil_jasa'] * 100)
                category['total_sisa_percent'] = (category['total_sisa'] / category['total_hasil_jasa'] * 100)
            else:
                category['total_pengeluaran_percent'] = 0
                category['total_spare_part_percent'] = 0
                category['total_sisa_percent'] = 0

        data = {
            'company_name': self.env.company.name,
            'date_start': self.date_start.strftime('%d-%m-%Y') if self.date_start else None,
            'date_end': self.date_end.strftime('%d-%m-%Y') if self.date_end else None,
            'year': self.year,
            'data': list(categories.values())
        }

        return self.env.ref('fleet_reporting.report_fleet_pendapatan_v2_action').report_action(self, data=data)
        
        