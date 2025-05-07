from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime

class MatchInvoicePaymentWizard(models.TransientModel):
    _name = 'match.invoice.wizard.payment'
    _description = 'Wizard to Confirm Payment with Attachment'

    invoice_id = fields.Many2one('account.move', string="Invoice", required=True, readonly=True)
    transaction_amount = fields.Monetary(string="Transaction Amount", required=True)
    attachment = fields.Binary(string="Upload File")
    attachment_filename = fields.Char("File Name")
    currency_id = fields.Many2one('res.currency', related='invoice_id.currency_id')

    def action_confirm_payment(self):
        for invoice in self.invoice_id:
            if invoice.state != 'posted':
                raise UserError(f"Invoice {invoice.name} must be posted before creating a payment.")
            if invoice.payment_state == 'paid':
                raise UserError(f"Invoice {invoice.name} is already paid.")
            print(self._context,"lllllllllllllllllllllllllllllllll")
            AkahuTransaction = self.env['akahu.transaction']
            match = AkahuTransaction.search([('reference', '=', self.invoice_id.reference)], limit=1)
            if match.match_status == 'matched':
                raise UserError(f"Transaction {match.name} is already matched.")
            clean_ctx = {
                'lang': 'en_US',
                'tz': 'Asia/Karachi',
                'uid': self.env.uid,
                'allowed_company_ids': self.env.context.get('allowed_company_ids'),
                'active_model': 'account.move',
                'active_ids': self.invoice_id.id,
            }

            wizard = self.env['account.payment.register'].with_context(clean_ctx).create({
                'amount': match.amount_due if match.match_status == 'partial' else  match.amount ,
                'journal_id': self.env['account.journal'].search([('type', '=', 'bank')], limit=1).id,
                'payment_date': fields.Date.today(),
            })
            payments = wizard._create_payments()  
            payments.attachment = self.attachment
            invoice.transaction_ref = match.name
            if match.amount < invoice.amount_total:
                match.amount_due = 0.0
                match.match_status = 'matched'
            elif match.amount == invoice.amount_total:
                match.amount_due = 0.0
                match.match_status = 'matched'
            else:
                match.amount_due = match.amount - invoice.amount_total
                match.match_status = 'partial'
            if payments:
                payments.write({'transaction_ref': match.name})
            

