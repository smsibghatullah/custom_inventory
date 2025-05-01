from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime

class MatchInvoiceWizard(models.TransientModel):
    _name = 'match.invoice.wizard'
    _description = 'Match Transaction with Invoices'

    transaction_ref = fields.Char('Transaction Reference')
    invoice_line_ids = fields.One2many('match.invoice.wizard.line', 'wizard_id', string='Invoices')


    def action_create_payments(self):
        for line in self.invoice_line_ids.filtered(lambda l: l.selected):
            invoice = line.invoice_id

            if invoice.state != 'posted':
                raise UserError(f"Invoice {invoice.name} must be posted before creating a payment.")
            if invoice.payment_state == 'paid':
                raise UserError(f"Invoice {invoice.name} is already paid.")
            clean_ctx = {
                'lang': 'en_US',
                'tz': 'Asia/Karachi',
                'uid': self.env.uid,
                'allowed_company_ids': self.env.context.get('allowed_company_ids'),
                'active_model': 'account.move',
                'active_ids': invoice.ids,
            }

            wizard = self.env['account.payment.register'].with_context(clean_ctx).create({
                'amount': invoice.amount_residual,
                'journal_id': self.env['account.journal'].search([('type', '=', 'bank')], limit=1).id,
                'payment_date': fields.Date.today(),
            })

            payment = wizard._create_payments()

            match = self.env['akahu.transaction'].search([('reference', '=', self.transaction_ref)], limit=1)
            transaction_name = match.name if match else ''
            transaction_ref = match.reference if match else ''
            
            invoice.write({
                'transaction_ref': transaction_name,
                'reference': transaction_ref,
            })
            if payment:
                payment.write({'transaction_ref': transaction_name})



class MatchInvoiceWizardLine(models.TransientModel):
    _name = 'match.invoice.wizard.line'
    _description = 'Invoice Line for Matching Wizard'

    wizard_id = fields.Many2one('match.invoice.wizard', required=True, ondelete='cascade')
    invoice_id = fields.Many2one('account.move', string='Invoice')
    name = fields.Char(related='invoice_id.name')
    partner_id = fields.Many2one(related='invoice_id.partner_id')
    amount_total = fields.Monetary(related='invoice_id.amount_total')
    amount_residual = fields.Monetary(related='invoice_id.amount_residual')
    currency_id = fields.Many2one(related='invoice_id.currency_id')
    invoice_date = fields.Date(related='invoice_id.invoice_date')
    payment_state = fields.Selection(related='invoice_id.payment_state')
    selected = fields.Boolean(string='Select')



