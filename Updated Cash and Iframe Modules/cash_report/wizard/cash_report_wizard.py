from odoo import models, fields, api
from datetime import datetime, timedelta

class CashReportWizard(models.TransientModel):
    _name = 'cash.report.wizard'
    _description = 'Cash Report Wizard'

    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=fields.Date.context_today
    )
    end_date = fields.Date(
        string='End Date',
        required=True,
        default=fields.Date.context_today
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    account_id = fields.Many2one(
        'account.account',
        string='Account',
        required=True,
        domain="[('account_type', '=', 'asset_cash')]"
    )

    @api.onchange('company_id')
    def _onchange_company_id(self):
        self.account_id = False
        if self.company_id:
            return {'domain': {'account_id': [
                ('company_id', '=', self.company_id.id),
                ('account_type', '=', 'asset_cash')
            ]}}

    def get_cash_report_data(self, data):
        query = """
            WITH RECURSIVE running_balance AS (
                SELECT 
                    am.name,
                    am.ref,
                    aml.name as description,
                    aml.date,
                    SUM(COALESCE(aml.debit, 0.0)) as debit,
                    SUM(COALESCE(aml.credit, 0.0)) as credit,
                    SUM(COALESCE(aml.balance, 0.0)) as balance
                FROM account_move_line aml
                JOIN account_move am ON am.id = aml.move_id
                WHERE 
                    am.state = 'posted'
                    AND aml.date BETWEEN %s AND %s
                    AND aml.company_id = %s
                    AND aml.account_id = %s
                GROUP BY am.name, am.ref, aml.name, aml.date
                ORDER BY aml.date, am.name
            )
            SELECT 
                name,
                ref,
                description,
                date,
                debit,
                credit,
                SUM(balance) OVER (ORDER BY date, name) as running_balance
            FROM running_balance
            ORDER BY date, name;
        """
        
        self.env.cr.execute(query, (
            data['start_date'], 
            data['end_date'], 
            data['company_id'],
            data['account_id']
        ))
        return self.env.cr.dictfetchall()

    def generate_report(self):
        self.ensure_one()
        data = {
            'start_date': self.start_date,
            'end_date': self.end_date,
            'company_id': self.company_id.id,
            'account_id': self.account_id.id,
            'account_name': self.account_id.name,
            'report_type': 'qweb-pdf',
        }
        return self.env.ref('cash_report.action_report_cash').report_action(self, data=data)