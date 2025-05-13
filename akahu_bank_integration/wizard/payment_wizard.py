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

            AkahuTransaction = self.env['akahu.transaction']
            match = AkahuTransaction.search([('reference', '=', invoice.reference)], limit=1)

            if match.match_status == 'matched':
                raise UserError(f"Transaction {match.name} is already matched.")

            clean_ctx = {
                'lang': 'en_US',
                'tz': 'Asia/Karachi',
                'uid': self.env.uid,
                'allowed_company_ids': self.env.context.get('allowed_company_ids'),
                'active_model': 'account.move',
                'active_ids': invoice.id,
            }

            payment_amount = min(abs(match.amount_due), abs(invoice.amount_residual))
            match.amount_paid += invoice.amount_residual if match.amount >= 0 else -invoice.amount_residual
            match.amount_due = match.amount - match.amount_paid
            print(match.amount_due,match.amount_paid,match.amount,"pppppppppppppppppppppppppppppppppdddddddddddddddddddd")

            if match.amount >= 0 and match.amount_due < 0:
                match.amount_due = 0.0
            elif match.amount < 0 and match.amount_due > 0:
                match.amount_due = 0.0

            if abs(match.amount_due) < 0.0001:
                match.match_status = 'matched'
                match.amount_due = 0.0
            else:
                match.match_status = 'partial'

            wizard = self.env['account.payment.register'].with_context(clean_ctx).create({
                'amount': payment_amount,
                'journal_id': self.env['account.journal'].search([('type', '=', 'bank')], limit=1).id,
                'payment_date': fields.Date.today(),
            })

            payments = wizard._create_payments()
            payments.attachment = self.attachment
            invoice.transaction_ref = match.name
            match.action_match_transaction()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Payment Success',
                    'message': 'Your payment was successfully processed.',
                    'type': 'success',  # types: success, warning, danger, info
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }


