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

  