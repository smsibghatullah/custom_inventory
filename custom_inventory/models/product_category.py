from odoo import models, fields

ACCOUNT_DOMAIN = "['&', ('deprecated', '=', False), ('account_type', 'not in', ('asset_receivable','liability_payable','asset_cash','liability_credit_card','off_balance'))]"

class ProductCategory(models.Model):
    _inherit = "product.category"

    sale_debit_account_id = fields.Many2one(
        'account.account', string="Sale Debit Account", domain=ACCOUNT_DOMAIN,company_dependent=True
    )
    sale_credit_account_id = fields.Many2one(
        'account.account', string="Sale Credit Account", domain=ACCOUNT_DOMAIN,company_dependent=True
    )
    sale_journal_id = fields.Many2one(
        'account.journal', string="Sale Journal", domain=[('type', '=', 'sale')]
    )
    purchase_debit_account_id = fields.Many2one(
        'account.account', string="Purchase Debit Account", domain=ACCOUNT_DOMAIN,company_dependent=True
    )
    purchase_credit_account_id = fields.Many2one(
        'account.account', string="Purchase Credit Account", domain=ACCOUNT_DOMAIN,company_dependent=True
    )
    purchase_journal_id = fields.Many2one(
        'account.journal', string="Purchase Journal", domain=[('type', '=', 'purchase')]
    )
