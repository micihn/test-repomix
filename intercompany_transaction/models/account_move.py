from odoo import api, fields, models, _
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = ['account.move', 'intercompany.mixin']
    _name = 'account.move'

    intercompany_state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting_approval', 'Waiting Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Inter Company Status', default='draft', tracking=True)

    intercompany_move_id = fields.Many2one(
        'account.move',
        string='Related Invoice/Bill',
        readonly=True,
        copy=False
    )

    auto_generated = fields.Boolean('Auto Generated', readonly=True, copy=False)


    def _prepare_intercompany_move_data(self):
        self.ensure_one()
        move_type = 'out_invoice' if self.move_type == 'in_invoice' else 'in_invoice'
        
        return {
            'move_type': move_type,
            'partner_id': self.company_id.partner_id.id,
            'company_id': self.partner_id.company_id.id,
            'is_intercompany_transaction': True,
            'ref': self.name,
            'invoice_date': self.invoice_date,
            'invoice_line_ids': [(0, 0, {
                'product_id': line.product_id.id,
                'name': line.name,
                'quantity': line.quantity,
                'price_unit': line.price_unit,
                'tax_ids': [(6, 0, line.tax_ids.ids)],
            }) for line in self.invoice_line_ids],
        }

    def action_post(self):
        """Override to handle inter-company validation logic"""
        for move in self:
            if move.is_intercompany_transaction:
                validation_type = move._get_validation_type()
                
                if validation_type == 'auto_validate':
                    # Auto validate both sides
                    if not move.intercompany_move_id:
                        move._create_intercompany_move()
                    super(AccountMove, move | move.intercompany_move_id).action_post()
                
                elif validation_type == 'dual_approval':
                    if move.intercompany_state != 'approved':
                        move.intercompany_state = 'waiting_approval'
                        return
                    
                    if not move.intercompany_move_id:
                        move._create_intercompany_move()
                        move.intercompany_move_id.intercompany_state = 'waiting_approval'
                    elif move.intercompany_move_id.intercompany_state == 'approved':
                        super(AccountMove, move | move.intercompany_move_id).action_post()
                    
                else:  # no_validation
                    if not move.intercompany_move_id:
                        move._create_intercompany_move()
                    super(AccountMove, move).action_post()
            
            else:
                super(AccountMove, move).action_post()

    def action_approve_intercompany(self):
        """Approve inter-company transaction"""
        self.ensure_one()
        self._check_approval_rights()
        self.intercompany_state = 'approved'
        
        # If both sides approved, post the moves
        if (self.intercompany_move_id and 
            self.intercompany_move_id.intercompany_state == 'approved'):
            self.action_post()

    def action_reject_intercompany(self):
        """Reject inter-company transaction"""
        self.ensure_one()
        self._check_approval_rights()
        self.intercompany_state = 'rejected'
        if self.intercompany_move_id:
            self.intercompany_move_id.intercompany_state = 'rejected'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if not record.auto_generated and record.move_type in ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']:
                company_id = record.partner_id.company_id
                if company_id and company_id != record.company_id:
                    config_param = self.env['ir.config_parameter'].sudo()
                    if config_param.get_param('intercompany_transaction.type') == 'sync_invoice':
                        record._create_counterpart_invoice()
        return records
    

    def _create_counterpart_invoice(self):
        """Create corresponding invoice/bill in partner's company"""
        self.ensure_one()
        if not self.partner_id.company_id:
            return

        AccountMove = self.env['account.move'].with_company(self.partner_id.company_id.id)
        
        # Determine move type
        move_type_map = {
            'out_invoice': 'in_invoice',
            'in_invoice': 'out_invoice',
            'out_refund': 'in_refund',
            'in_refund': 'out_refund'
        }
        counterpart_type = move_type_map.get(self.move_type)
        if not counterpart_type:
            return

        # Prepare invoice lines
        invoice_lines = []
        for line in self.invoice_line_ids:
            invoice_lines.append((0, 0, {
                'name': line.name,
                'product_id': line.product_id.id,
                'quantity': line.quantity,
                'price_unit': line.price_unit,
                'tax_ids': [(6, 0, line.tax_ids.ids)],
                'account_id': line.account_id.id,  # You might need to map accounts between companies
            }))

        # Create counterpart invoice/bill
        move_vals = {
            'partner_id': self.company_id.partner_id.id,
            'company_id': self.partner_id.company_id.id,
            'move_type': counterpart_type,
            'is_intercompany_transaction': True,
            'auto_generated': True,
            'ref': self.name,
            'invoice_date': self.invoice_date,
            'invoice_line_ids': invoice_lines,
        }

        counterpart_move = AccountMove.create(move_vals)
        self.write({
            'is_intercompany_transaction': True,
            'intercompany_move_id': counterpart_move.id
        })
        return counterpart_move

    def _create_intercompany_move(self):
        """Create corresponding invoice/bill for inter-company transaction"""
        for move in self:
            if not move.is_intercompany_transaction and not move.intercompany_move_id:
                move_data = move._prepare_intercompany_move_data()
                intercompany_move = self.with_company(move_data['company_id']).create(move_data)
                move.write({
                    'is_intercompany_transaction': True,
                    'intercompany_move_id': intercompany_move.id
                })
                intercompany_move.write({
                    'intercompany_move_id': move.id
                })

