from odoo import models, fields

class ProductCategory(models.Model):
    _inherit = "product.category"

    sale_debit_account_id = fields.Many2one(
        'account.account', string="Sale Debit Account", domain=[('deprecated', '=', False)],company_dependent=True
    )
    sale_credit_account_id = fields.Many2one(
        'account.account', string="Sale Credit Account", domain=[('deprecated', '=', False)],company_dependent=True
    )
    sale_journal_id = fields.Many2one(
        'account.journal', string="Sale Journal", domain=[('type', '=', 'sale')],company_dependent=True
    )
    purchase_debit_account_id = fields.Many2one(
        'account.account', string="Purchase Debit Account", domain=[('deprecated', '=', False)],company_dependent=True
    )
    purchase_credit_account_id = fields.Many2one(
        'account.account', string="Purchase Credit Account", domain=[('deprecated', '=', False)],company_dependent=True
    )
    purchase_journal_id = fields.Many2one(
        'account.journal', string="Purchase Journal", domain=[('type', '=', 'purchase')],company_dependent=True
    )
