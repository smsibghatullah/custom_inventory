from odoo import models, fields,api

class AkahuTransactionLink(models.Model):
    _name = 'akahu.transaction.link'
    _description = 'Link Between Akahu Transactions and Invoices'

    name = fields.Char(string='Reference', required=True)
    akahu_account_id = fields.Many2one('akahu.bank.account', string="Akahu Account", required=True)  
    invoice_ids = fields.Many2many(
        'account.move',
        'akahu_link_account_move_rel',
        'link_id',
        'invoice_id',
        string="Linked Invoices"
    )

    transaction_ids = fields.Many2many(
        'akahu.transaction',
        'akahu_link_transaction_rel',
        'link_id',
        'transaction_id',
        string="Linked Akahu Transactions"
    )

    total_transactions = fields.Integer(string="All Transactions", compute="_compute_transaction_counts")
    matched_transactions = fields.Integer(string="Matched", compute="_compute_transaction_counts")
    unmatched_transactions = fields.Integer(string="Unmatched", compute="_compute_transaction_counts")
    partial_matched_transactions = fields.Integer(string="Partial Matched", compute="_compute_transaction_counts")

    @api.depends('transaction_ids.match_status')
    def _compute_transaction_counts(self):
        for rec in self:
            transactions = rec.transaction_ids
            rec.total_transactions = len(transactions)
            rec.matched_transactions = len(transactions.filtered(lambda t: t.match_status == 'matched'))
            rec.partial_matched_transactions = len(transactions.filtered(lambda t: t.match_status == 'partial'))
            rec.unmatched_transactions = len(transactions.filtered(lambda t: t.match_status == 'unmatched'))


    def action_dummy(self):
        print('12345')

  