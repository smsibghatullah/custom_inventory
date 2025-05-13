from odoo import models, fields, api
import requests
import logging
from datetime import datetime, timedelta
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class AkahuTransaction(models.Model):
    _name = 'akahu.transaction'
    _description = 'Akahu Bank Transaction'
    _order = 'date desc'

    name = fields.Char(string="Transaction ID")  
    akahu_account_id = fields.Char(string="Akahu Account")  
    akahu_user_id = fields.Char(string="Akahu User ID")  
    akahu_connection_id = fields.Char(string="Connection ID") 

    created_at = fields.Datetime(string="Created At")  
    updated_at = fields.Datetime(string="Updated At") 
    date = fields.Datetime(string="Transaction Date")  

    description = fields.Char(string="Description")  
    amount = fields.Float(string="Amount")  
    balance = fields.Float(string="Balance After Transaction")  
    type = fields.Selection([
        ('PAYMENT', 'Payment'),
        ('TRANSFER', 'Transfer'),
        ('INCOME', 'Income'),
        ('OTHER', 'Other')
    ], string="Transaction Type")  

    hash = fields.Char(string="Hash")  

    particulars = fields.Char(string="Particulars")  
    code = fields.Char(string="Code")  
    reference = fields.Char(string="Reference")  
    other_account = fields.Char(string="Other Account") 
    transaction_link_id = fields.Many2one('akahu.transaction.link', string="Transaction Link")
    match_status = fields.Selection([
        ('matched', 'Matched'),
        ('partial', 'Partial Match'),
        ('unmatched', 'Unmatched'),
    ], string="Status", default='unmatched')
    amount_due = fields.Float(string="Amount Due")
    amount_paid = fields.Float(string="Amount Paid")

   
 
    @staticmethod
    def parse_datetime_safe(value):
        """Parse ISO datetime string safely, return None if value is None or malformed."""
        if value:
            try:
                return datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%fZ')
            except ValueError:
                try:
                    return datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ')
                except ValueError:
                    _logger.warning("Invalid datetime format: %s", value)
        return None

    def sync_transactions(self):
        """Sync transactions from Akahu API"""
        headers = {
            'Authorization': 'Bearer user_token_cm9y2t9w2000208l1c7ts2m2i',
            'X-Akahu-Id': 'app_token_cm9y2t9w2000108l1bdnc7mza'
        }

        response = requests.get(
            'https://api.akahu.io/v1/transactions',
            headers=headers
        )

        if response.status_code == 200:
            transactions = response.json()
            for trans_data in transactions.get('items', []):
                if trans_data.get('_id') != self.reference:
                        continue  
                transaction_type = 'INCOME' if trans_data.get('type') == 'credit' else 'PAYMENT'
                self.write({
                    'name': trans_data.get('description'),
                    'amount': trans_data.get('amount'),
                    'date': self.parse_datetime_safe(trans_data.get('date')),
                    'created_at': self.parse_datetime_safe(trans_data.get('created_at')),
                    'updated_at': self.parse_datetime_safe(trans_data.get('updated_at')),
                    'balance': trans_data.get('balance'),
                    'type': transaction_type,  
                    # 'status': 'completed',
                    'reference': trans_data.get('_id'),
                    'hash': trans_data.get('hash'),
                    'akahu_account_id': trans_data.get('_account'),
                    'akahu_user_id': trans_data.get('_user'),
                    'akahu_connection_id': trans_data.get('_connection'),
                    'description': trans_data.get('description'),
                    'particulars': trans_data.get('meta', {}).get('particulars'),
                    'code': trans_data.get('meta', {}).get('code'),
                    'other_account': trans_data.get('meta', {}).get('other_account'),
                })
        else:
            _logger.error('Failed to fetch transactions: %s', response.text)


    def action_match_transaction(self):
            for transaction in self:
                transaction_reference = transaction.reference
                transaction_amount = round(transaction.amount_due, 2)
                if self.amount > 0:
                    move_types = ['out_invoice', 'in_refund']
                else:
                    move_types = ['in_invoice', 'out_refund']
                matching_invoices = self.env['account.move'].search([
                    '&',
                        '&',
                            ('state', '=', 'posted'),
                            ('payment_state', 'in', ['not_paid', 'partial']),
                        ('move_type', 'in', move_types),
                    '|',
                        ('reference', '=', transaction_reference),
                        ('amount_total', '=', transaction_amount),
                ])
                print(matching_invoices,"ppppppppppppppppppppppppsssssssssssssmatching_invoicess")

                if matching_invoices:
                    transaction.transaction_link_id.invoice_ids = [(6, 0, matching_invoices.ids)]
                else:
                    transaction.transaction_link_id.invoice_ids = [(6, 0, [])]
            return True

    def action_match_invoice(self):
        self.ensure_one()

        if self.match_status == 'matched':
            raise UserError(f"Transaction {self.name} is already matched.")

        if self.amount > 0:
            move_types = ['out_invoice', 'in_refund']
        else:
            move_types = ['in_invoice', 'out_refund']

        invoices = self.env['account.move'].search([
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('move_type', 'in', move_types),
        ])

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'match.invoice.wizard',
            'view_mode': 'form',
            'name': 'Match Invoices',
            'target': 'new',
            'context': {
                'default_transaction_ref': self.reference,
                'default_invoice_line_ids': [
                    (0, 0, {'invoice_id': inv.id}) for inv in invoices
                ]
            },
        }


