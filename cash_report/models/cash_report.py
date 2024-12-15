from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime, timedelta

class CashReport(models.Model):
    _name = 'cash.report'
    _description = 'Cash Account Report'

    @api.model
    def get_cash_report_data(self, data):
        query = """
            WITH opening_balance AS (
                -- Calculate balance before start date
                SELECT COALESCE(SUM(aml.balance), 0) as opening_balance
                FROM account_move_line aml
                JOIN account_move am ON am.id = aml.move_id
                WHERE 
                    am.state = 'posted'
                    AND aml.date < %s
                    AND aml.company_id = %s
                    AND aml.account_id = %s
            ),
            running_balance AS (
                SELECT 
                    am.name,
                    am.ref,
                    aml.name as description,
                    aml.date,
                    aml.debit,
                    aml.credit,
                    aml.balance,
                    (SELECT opening_balance FROM opening_balance) as initial_balance
                FROM account_move_line aml
                JOIN account_move am ON am.id = aml.move_id
                WHERE 
                    am.state = 'posted'
                    AND aml.date BETWEEN %s AND %s
                    AND aml.company_id = %s
                    AND aml.account_id = %s
                ORDER BY aml.date, am.name
            )
            SELECT 
                name,
                ref,
                description,
                date,
                debit,
                credit,
                initial_balance + SUM(balance) OVER (ORDER BY date, name) as running_balance
            FROM running_balance
            ORDER BY date, name;
        """
        
        self.env.cr.execute(query, (
            data['start_date'],  # For opening balance
            data['company_id'],
            data['account_id'],
            data['start_date'],  # For date range
            data['end_date'],
            data['company_id'],
            data['account_id']
        ))
        
        result = self.env.cr.dictfetchall()
        
        # Add opening balance as first row if there is an opening balance
        opening_balance = result[0]['running_balance'] - result[0]['debit'] + result[0]['credit'] if result else 0
        if opening_balance != 0:
            prev_date = fields.Date.from_string(data['start_date']) - timedelta(days=1)
            result.insert(0, {
                'name': 'Opening Balance',
                'ref': '',
                'description': f"Balance before {data['start_date']}",
                'date': prev_date,
                'debit': opening_balance if opening_balance > 0 else 0,
                'credit': -opening_balance if opening_balance < 0 else 0,
                'running_balance': opening_balance
            })
        
        return result