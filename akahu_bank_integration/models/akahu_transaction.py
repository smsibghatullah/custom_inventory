from odoo import models, fields, api
import requests
import logging
from datetime import datetime, timedelta
from odoo.exceptions import UserError
from itertools import combinations

_logger = logging.getLogger(__name__)

class AkahuTransaction(models.Model):
    _name = 'akahu.transaction'
    _description = 'Akahu Bank Transaction'
    _order = 'date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Transaction ID")  
    akahu_account_id = fields.Char(string="Akahu Account")  
    akahu_user_id = fields.Char(string="Akahu User ID")  
    akahu_connection_id = fields.Char(string="Connection ID") 

    created_at = fields.Datetime(string="Created At")  
    updated_at = fields.Datetime(string="Updated At") 
    date = fields.Char(string="Transaction Date")
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
    comment_line_ids = fields.One2many(
        'transaction.comment.line',
        'transaction_id',
        string='Comments History',
        readonly=True,
    )
    has_comment = fields.Boolean(
        string="Has Comment",
        compute="_compute_has_comment",
        store=False
    )

    def _compute_has_comment(self):
        for rec in self:
            rec.has_comment = bool(rec.comment_line_ids)


    def action_open_comment_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Comment',
            'res_model': 'transaction.comment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
             'default_transaction_id': self.id,
             'default_amount':self.amount,
             'default_show_history':False
            },
        }
 
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
        all_ids_criteria_1 = []
        all_ids_criteria_2 = []
        all_ids_criteria_3 = []
        all_ids_criteria_4 = []
        all_ids_criteria_5 = []

        for transaction in self:
            transaction_amount = round(transaction.amount_due, 2)

            if transaction.amount > 0:
                move_types = ['out_invoice', 'in_refund']
            else:
                move_types = ['in_invoice', 'out_refund']

            # ------------------- CRITERIA 1 -------------------
            matching_invoices = self.env['account.move'].search([
                ('state', '=', 'posted'),
                ('payment_state', 'in', ['not_paid', 'partial']),
                ('move_type', 'in', move_types),
                '|',
                    ('partner_id.name', '=', transaction.name),
                    ('amount_total', '=', transaction_amount),
            ])
            all_ids_criteria_1.extend(matching_invoices.ids)

            # ------------------- CRITERIA 2 -------------------
            matching_invoices_criteria_2 = self.env['account.move'].search([
                ('state', '=', 'posted'),
                ('payment_state', 'in', ['not_paid', 'partial']),
                ('move_type', 'in', move_types),
                '|','|','|',
                    ('name', '=', transaction.reference),
                    ('invoice_origin', '=', transaction.reference),
                    ('reference', '=', transaction.code),
                    ('reference', '=', transaction.reference),
            ])
            all_ids_criteria_2.extend(matching_invoices_criteria_2.ids)

            # ------------------- CRITERIA 3 -------------------
            matching_invoices_criteria_3 = self.env['account.move'].search([
                ('state', '=', 'posted'),
                ('payment_state', 'in', ['not_paid', 'partial']),
                ('move_type', 'in', move_types),
                '|', '|',
                    ('amount_total', '=', transaction_amount),
                    ('reference', '=', transaction.code),
                    ('reference', '=', transaction.reference),
            ])
            all_ids_criteria_3.extend(matching_invoices_criteria_3.ids)

            # ------------------- CRITERIA 4 -------------------
            matching_partners = self.env['res.partner'].search([
                ('name', 'ilike', transaction.name)
            ]).ids

            matching_invoices_criteria_4 = self.env['account.move'].search([
                ('state', '=', 'posted'),
                ('payment_state', 'in', ['not_paid', 'partial']),
                ('move_type', 'in', move_types),
                '|',
                    ('partner_id', 'in', matching_partners),
                    '&',
                        ('amount_total', '>=', transaction.amount - 10),
                        ('amount_total', '<=', transaction.amount + 10),
            ])
            all_ids_criteria_4.extend(matching_invoices_criteria_4.ids)

            # ------------------- CRITERIA 5 (Multiple Invoices Sum) -------------------
            partners_criteria_5 = self.env['res.partner'].search([
                    ('name', '=', transaction.name),
            ]).ids

            candidate_invoices = self.env['account.move'].search([
                ('state', '=', 'posted'),
                ('payment_state', 'in', ['not_paid', 'partial']),
                ('move_type', 'in', move_types),
                '|',
                ('partner_id', 'in', partners_criteria_5),
                ('reference', '=', transaction.reference)

            ])

            tolerance = 0.05
            invoice_list = list(candidate_invoices)

            for r in range(1, len(invoice_list) + 1):
                for combo in combinations(invoice_list, r):
                    total = round(sum(inv.amount_total for inv in combo), 2)
                    if abs(total - transaction_amount) <= tolerance:
                        all_ids_criteria_5.extend(inv.id for inv in combo)

        all_ids_criteria_1 = list(set(all_ids_criteria_1))
        all_ids_criteria_2 = list(set(all_ids_criteria_2))
        all_ids_criteria_3 = list(set(all_ids_criteria_3))
        all_ids_criteria_4 = list(set(all_ids_criteria_4))
        all_ids_criteria_5 = list(set(all_ids_criteria_5))

        self.transaction_link_id.invoice_ids = [(6, 0, all_ids_criteria_1)]
        self.transaction_link_id.invoice_ids_criteria_2 = [(6, 0, all_ids_criteria_2)]
        self.transaction_link_id.invoice_ids_criteria_3 = [(6, 0, all_ids_criteria_3)]
        self.transaction_link_id.invoice_ids_criteria_4 = [(6, 0, all_ids_criteria_4)]
        self.transaction_link_id.invoice_ids_criteria_5 = [(6, 0, all_ids_criteria_5)]

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

class TransactionCommentLine(models.Model):
    _name = 'transaction.comment.line'
    _description = 'Transaction Comment Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    transaction_id = fields.Many2one('akahu.transaction', string='Transaction', required=True, ondelete='cascade')
    comment = fields.Text(string='Comment', required=True, tracking=True)
    amount = fields.Monetary(string='Amount', currency_field='currency_id')
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    create_uid = fields.Many2one('res.users', string='Added By', readonly=True)
    create_date = fields.Datetime(string='Date', readonly=True)
    currency_id = fields.Many2one('res.currency', readonly=True)

