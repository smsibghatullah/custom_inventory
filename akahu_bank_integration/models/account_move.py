from odoo import models, fields, api
import requests
import logging
from datetime import datetime
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    transaction_ref = fields.Char(string="Transaction Refrence")  
   

    def action_paid_invoice(self):
        for invoice in self:
            if invoice.state != 'posted':
                raise UserError(f"Invoice {invoice.name} must be posted before creating a payment.")
            if invoice.payment_state == 'paid':
                raise UserError(f"Invoice {invoice.name} is already paid.")
            print(self._context,"lllllllllllllllllllllllllllllllll")
            wizard = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
                'amount': invoice.amount_residual,
                'journal_id': self.env['account.journal'].search([('type', '=', 'bank')], limit=1).id,
                'payment_date': fields.Date.today(),
            })
            payments = wizard._create_payments()  
            AkahuTransaction = self.env['akahu.transaction']
            match = AkahuTransaction.search([('reference', '=', self.reference)], limit=1)
            invoice.transaction_ref = match.name
            if payments:
                payments.write({'transaction_ref': match.name})
            


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    transaction_ref = fields.Char(string="Transaction Refrence") 
    effective_date = fields.Date(string='Effective Date')
    bank_reference = fields.Char(string='Bank Reference') 
    cheque_reference = fields.Char(string='Cheque Reference')

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    invoice_id = fields.Many2one('account.move', string="Invoice")
