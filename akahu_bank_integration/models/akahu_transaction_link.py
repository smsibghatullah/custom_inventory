from odoo import models, fields, api

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
        string="Linked Invoices",
    )

    invoice_ids_criteria_2 = fields.Many2many(
        'account.move',
        'akahu_link_account_move_rel2',
        'link_id',
        'invoice_id',
        string="Linked Invoices",
    )

    invoice_ids_criteria_3 = fields.Many2many(
        'account.move',
        'akahu_link_account_move_rel3',
        'link_id',
        'invoice_id',
        string="Linked Invoices",
    )

    invoice_ids_criteria_4 = fields.Many2many(
        'account.move',
        'akahu_link_account_move_rel4',
        'link_id',
        'invoice_id',
        string="Linked Invoices",
    )

    invoice_ids_criteria_5 = fields.Many2many(
        'account.move',
        'akahu_link_account_move_rel5',
        'link_id',
        'invoice_id',
        string="Linked Invoices",
    )

    all_transaction_ids = fields.Many2many(
        'akahu.transaction',
        'akahu_link_transaction_rel',
        'link_id',
        'transaction_id',
        string="All Linked Transactions"
    )

    transaction_ids = fields.Many2many(
        'akahu.transaction',
        string="Filtered Transactions",
        compute='_compute_filtered_transactions',
        store=True
    )

    filter_match_status = fields.Selection([
        ('all', 'All'),
        ('matched', 'Matched'),
        ('partial', 'Partial'),
        ('unmatched', 'Unmatched')
    ], string="Filter", default='all')

    total_transactions = fields.Integer(string="All Transactions", compute="_compute_transaction_counts")
    matched_transactions = fields.Integer(string="Matched", compute="_compute_transaction_counts")
    unmatched_transactions = fields.Integer(string="Unmatched", compute="_compute_transaction_counts")
    partial_matched_transactions = fields.Integer(string="Partial Matched", compute="_compute_transaction_counts")
        


    @api.depends('all_transaction_ids.match_status')
    def _compute_transaction_counts(self):
        for rec in self:
            rec.total_transactions = len(rec.all_transaction_ids)
            rec.matched_transactions = len(rec.all_transaction_ids.filtered(lambda t: t.match_status == 'matched'))
            rec.partial_matched_transactions = len(rec.all_transaction_ids.filtered(lambda t: t.match_status == 'partial'))
            rec.unmatched_transactions = len(rec.all_transaction_ids.filtered(lambda t: t.match_status == 'unmatched'))

    @api.depends('filter_match_status', 'all_transaction_ids.match_status')
    def _compute_filtered_transactions(self):
        for rec in self:
            if rec.filter_match_status == 'matched':
                rec.transaction_ids = rec.all_transaction_ids.filtered(lambda t: t.match_status == 'matched')
            elif rec.filter_match_status == 'partial':
                rec.transaction_ids = rec.all_transaction_ids.filtered(lambda t: t.match_status == 'partial')
            elif rec.filter_match_status == 'unmatched':
                rec.transaction_ids = rec.all_transaction_ids.filtered(lambda t: t.match_status == 'unmatched')
            else:
                rec.transaction_ids = rec.all_transaction_ids

    def action_filter_all(self):
        self.write({'filter_match_status': 'all'})
        self.invoice_ids = [(6, 0, [])]

    def action_filter_matched(self):
        self.write({'filter_match_status': 'matched'})
        self.invoice_ids = [(6, 0, [])]

    def action_filter_partial(self):
        self.write({'filter_match_status': 'partial'})
        self.invoice_ids = [(6, 0, [])]

    def action_filter_unmatched(self):
        self.write({'filter_match_status': 'unmatched'})
        self.invoice_ids = [(6, 0, [])]




