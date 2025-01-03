from odoo import api, fields, models
from datetime import datetime
from odoo.exceptions import UserError, ValidationError
import logging
import traceback

_logger = logging.getLogger(__name__)

class ReturnProduct(models.TransientModel):
    _name = 'return.product.service'
    _description = 'Return Product services'
    product_line = fields.One2many('return.product.service.line', 'wizard_id', 'Line')
    def process_return(self):
        services = self.env['fleet.vehicle.log.services'].browse(self._context.get('active_ids', []))
        for line in self.product_line:
            if line.product_qty > line.product_return_limit:
                raise UserError("Anda memasukkan jumlah Qty melebihi batas Limit Qty Return. " + str(line.product_id.name) + " memiliki limit return sebanyak " + str(line.product_return_limit))
        returned_product = []
        for line in self.product_line:
            if line.product_qty > 0:
                returned_product_dict = {
                    'product_name': line.product_id.name,
                    'product_id': line.product_id.id,
                    'product_qty': line.product_qty,
                    'product_cost': line.cost,
                }
                returned_product.append(returned_product_dict)
        # Membuat Service List khusus barang yang di return
        return_service = self.env['fleet.vehicle.log.services'].create({
            'description': str(services.name) + " - Return",
            'date': fields.Date.today(),
            'service_type_id': services.service_type_id.id,
            'vehicle_id': services.vehicle_id.id,
            'purchaser_id': services.purchaser_id.id,
            'is_service': False,
            'initial': False,
        })
        for product in returned_product:
            self.env['product.service.line'].create({
                'service': return_service.id,
                'product_id': product['product_id'],
                'product_qty': product['product_qty'] * -1,
                'cost': product['product_cost'] if bool(product['product_cost']) else self.env['product.product'].search([('id','=',product['product_id'])]).standard_price,
            })
        return_service.state_record = 'selesai'
        # Mengurangi maximum return limit untuk barang yang direturn
        for product in returned_product:
            product_line = self.env['product.service.line'].search([('service', '=', services.id), ('product_id', '=', product['product_id'])])
            product_line.product_return_limit = product_line.product_return_limit - product['product_qty']
        # Membuat Picking Return & Create
        picking_values = {
            'origin': services.name + str(" - Return"),
            'location_id': self.env['stock.location'].search([('name', '=', 'Internal Consumption')]).id,
            'location_dest_id': self.env['stock.picking.type'].search([('name', '=', 'Keluar Barang')]).default_location_src_id.id,
            'picking_type_id': self.env['stock.picking.type'].search([('name', '=', 'Keluar Barang')]).id,
        }

        picking = self.env['stock.picking'].create(picking_values)

        # Membuat picking line
        for product in returned_product:
            move_values = {
                'name': product['product_name'],
                'product_id': product['product_id'],
                'product_uom_qty': product['product_qty'],
                'quantity_done': product['product_qty'],
                'picking_id': picking.id,
                'location_id': picking.location_id.id,
                'location_dest_id': picking.location_dest_id.id,
                'state': 'draft',
                'price_unit': product['product_cost'],  # Use user input for unit cost
            }
            self.env['stock.move'].create(move_values)
        picking.action_confirm()
        picking.button_validate()

        # Melakukan revisi journal entry line berdasarkan cost yang diinput
        # Search for the journal entries related to the return picking
        try:
            return_picking = self.env['stock.picking'].search([('origin', '=', f"{services.name} - Return")], limit=1)
            if not return_picking:
                raise UserError(f"Return picking for service {services.name} - Return not found.")

            # Search for the journal entries based on the return picking's name
            journals = self.env['account.move'].sudo().search([
                ('ref', 'like', f"{return_picking.name}%")  # Matching the return picking name
            ])
            _logger.info(f"Found {len(journals)} journal entries for service {services.name} - Return")

            if not journals:
                raise UserError(f"No journal entries found for service {services.name} - Return")
    
            for journal in journals:
                for line in journal.line_ids:
                    if line.debit > 0:
                        line.with_context(check_move_validity=False).write({'debit': (product['product_cost'] * product['product_qty'])})
                    if line.credit > 0:
                        line.with_context(check_move_validity=False).write({'credit': (product['product_cost'] * product['product_qty'])})
        
        except Exception as e:
            _logger.error(f"Error processing journal entries: {str(e)}")
            raise UserError(f"Error processing journal entries: {str(e)}")


    # Get the action for fleet.vehicle.log.services form view
        action = self.env.ref('fleet.fleet_vehicle_log_services_action').read()[0]

        # Set the context to open the form view for the newly created return_service
        action['views'] = [(self.env.ref('fleet.fleet_vehicle_log_services_view_form').id, 'form')]
        action['res_id'] = return_service.id
        # Return the action
        return action
    @api.model
    def default_get(self, active_ids):
        default_vals = super(ReturnProduct, self).default_get(active_ids)
        active_id = self._context.get('active_id')
        services = self.env['fleet.vehicle.log.services'].browse(active_id)
        list_barang = []
        for record in services.list_sparepart:
            list_barang.append((0,0,{
                'product_id': record.product_id.id,
                'product_qty': 0,
                'maximum_qty': record.product_qty,
                'product_return_limit': record.product_return_limit,
            }))
        # default_vals['product_line'] = list_barang
        default_vals['product_line'] = list_barang
        return default_vals
class ReturnProductLine(models.TransientModel):
    _name = "return.product.service.line"
    product_id = fields.Many2one('product.product', string="Product", required=True, readonly=True, domain="[('id', '=', product_id)]")
    product_qty = fields.Float("Quantity", required=True)
    maximum_qty = fields.Float("Maximum Qty", readonly=True)
    cost = fields.Float("Cost")
    product_return_limit = fields.Float("Product Return Limit", readonly=True)
    wizard_id = fields.Many2one('return.product.service', string="Wizard")
    move_id = fields.Many2one('stock.move', "Move")
    @api.onchange('product_qty')
    def check_maximum_qty(self):
        for line in self:
            if line.product_qty > line.maximum_qty:
                line.product_qty = 0
                raise UserError("Quantity return yang dimasukkan melebihi quantity yang sebelumnya digunakan untuk service.")