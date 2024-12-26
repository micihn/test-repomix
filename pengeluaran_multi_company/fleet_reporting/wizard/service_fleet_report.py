from odoo import api, fields, models

class ServiceFleetReport(models.TransientModel):
    _name = 'service.fleet.report'
    _description = 'Service Fleet Report Wizard'

    semua_kendaraan = fields.Boolean(string='Semua Kendaraan', default=False)
    rekap = fields.Boolean(string='Rekap', default=False)  # New field
    kendaraan = fields.Many2one('fleet.vehicle')
    model_id = fields.Many2one('fleet.vehicle.model', string='Model')
    model_year = fields.Char(string='Model Year')
    tanggal_start = fields.Date()
    tanggal_finish = fields.Date()
    services = fields.Many2many('fleet.vehicle.log.services', 'services_list')

    @api.onchange('semua_kendaraan')
    def _onchange_semua_kendaraan(self):
        if self.semua_kendaraan:
            self.kendaraan = False
        else:
            self.rekap = False  

    @api.onchange('kendaraan')
    def _onchange_kendaraan(self):
        if self.kendaraan:
            self.semua_kendaraan = False
            self.model_id = False
            self.model_year = False

    @api.onchange('model_id', 'model_year')
    def _onchange_model_filters(self):
        if self.model_id or self.model_year:
            self.semua_kendaraan = False
            self.kendaraan = False

    @api.onchange('kendaraan', 'tanggal_start', 'tanggal_finish', 'semua_kendaraan', 'model_id', 'model_year')
    def _onchange_filters(self):
        if self.tanggal_start and self.tanggal_finish:
            domain = [
                ('date', '>=', self.tanggal_start),
                ('date', '<=', self.tanggal_finish),
                ('state_record', '=', 'selesai'),
            ]
            
            if not self.semua_kendaraan:
                if self.kendaraan:
                    domain.append(('vehicle_id', '=', self.kendaraan.id))
                else:
                    if self.model_id:
                        domain.append(('vehicle_id.model_id', '=', self.model_id.id))
                    if self.model_year:
                        domain.append(('vehicle_id.model_year', '=', self.model_year))

            services = self.env['fleet.vehicle.log.services'].search(domain)

            if services:
                self.services = services.ids
            else:
                self.services = [(5, 0, 0)]
        else:
            self.services = [(5, 0, 0)]

    def generate_report(self):
        if self.semua_kendaraan and self.rekap:
            # Generate summarized report
            domain = [
                ('date', '>=', self.tanggal_start),
                ('date', '<=', self.tanggal_finish),
                ('state_record', '=', 'selesai'),
            ]
            
            # Add model and year filters if specified
            if self.model_id:
                domain.append(('vehicle_id.model_id', '=', self.model_id.id))
            if self.model_year:
                domain.append(('vehicle_id.model_year', '=', self.model_year))
                
            services = self.env['fleet.vehicle.log.services'].search(domain)
            
            vehicle_summaries = {}
            
            for record in services:
                vehicle_id = record.vehicle_id
                if vehicle_id not in vehicle_summaries:
                    vehicle_summaries[vehicle_id] = {
                        'kendaraan': vehicle_id.name,
                        'license_plate': vehicle_id.license_plate,
                        'model': vehicle_id.model_id.name,
                        'model_year': vehicle_id.model_year,
                        'total_sparepart': 0,
                        'total_service': 0
                    }
                
                if record.service_type_id.category == 'sparepart':
                    total_sparepart = sum(item.total_cost for item in record.list_sparepart if item.product_qty != 0)
                    vehicle_summaries[vehicle_id]['total_sparepart'] += total_sparepart
                elif record.service_type_id.category == 'service':
                    vehicle_summaries[vehicle_id]['total_service'] += record.total_amount

            # Convert to list and add total
            summary_list = []
            for summary in vehicle_summaries.values():
                summary['total'] = summary['total_sparepart'] + summary['total_service']
                summary_list.append(summary)

            # Sort by license plate
            summary_list = sorted(summary_list, key=lambda x: x['license_plate'])

            data = {
                'tanggal_start': self.tanggal_start.strftime('%d-%m-%Y'),
                'tanggal_finish': self.tanggal_finish.strftime('%d-%m-%Y'),
                'semua_kendaraan': self.semua_kendaraan,
                'rekap': self.rekap,
                'model': self.model_id.name if self.model_id else '',
                'model_year': self.model_year if self.model_year else '',
                'summaries': summary_list
            }
            return self.env.ref('fleet_reporting.report_service_fleet_rekap_action').report_action([], data=data)
        service_list_unsorted = []
        for record in self.services:
            if record.service_type_id.category == 'service':
                service_dictionary = {
                    'service_category': record.service_type_id.category,
                    'description': record.description,
                    'service_type_id': record.service_type_id.name,
                    'date': record.date.strftime('%d/%m/%Y'),
                    'amount': record.amount,
                    'qty': 1,
                    'total_amount': record.total_amount,
                    'kendaraan': record.vehicle_id.name,
                    'license_plate': record.vehicle_id.license_plate,
                    'model': record.vehicle_id.model_id.name,
                    'model_year': record.vehicle_id.model_year,
                }
            elif record.service_type_id.category == 'sparepart':
                service_dictionary = {
                    'service_category': record.service_type_id.category,
                    'description': record.description,
                    'service_type_id': record.service_type_id.name,
                    'date': record.date.strftime('%d/%m/%Y'),
                    'kendaraan': record.vehicle_id.name,
                    'license_plate': record.vehicle_id.license_plate,
                    'model': record.vehicle_id.model_id.name,
                    'model_year': record.vehicle_id.model_year,
                }

                items = []
                for item in record.list_sparepart:
                    if item.product_qty != 0:
                        item_dict = {
                            'product_name': item.product_id.name,
                            'product_qty': item.product_qty,
                            'product_cost': item.cost,
                            'product_total_cost': item.total_cost,
                            'product_barcode': item.product_id.default_code,
                        }

                        items.append(item_dict)

                service_dictionary['items'] = items

            service_list_unsorted.append(service_dictionary)

        service_list = sorted(service_list_unsorted, key=lambda x: x['date'], reverse=True)

        data = {
            'tanggal_start': self.tanggal_start.strftime('%d-%m-%Y'),
            'tanggal_finish': self.tanggal_finish.strftime('%d-%m-%Y'),
            'kendaraan': 'Semua Kendaraan' if self.semua_kendaraan else (self.kendaraan.name if self.kendaraan else ''),
            'license_plate': '' if self.semua_kendaraan else (self.kendaraan.license_plate if self.kendaraan else ''),
            'model': self.model_id.name if self.model_id else '',
            'model_year': self.model_year if self.model_year else '',
            'services': service_list,
            'semua_kendaraan': self.semua_kendaraan,
        }
        return self.env.ref('fleet_reporting.report_service_fleet_action').report_action([], data=data)