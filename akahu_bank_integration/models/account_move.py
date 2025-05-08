from odoo import models, fields, api
import requests
import logging
from datetime import datetime
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    transaction_ref = fields.Char(string="Transaction Refrence")  
   

    def action_open_payment_wizard(self):
        AkahuTransaction = self.env['akahu.transaction']
        match = AkahuTransaction.search([('reference', '=', self.reference)], limit=1)
        if match.match_status == 'matched':
                raise UserError(f"Transaction {match.name} is already matched.")
        return {
            'name': 'Confirm Invoice Payment',
            'type': 'ir.actions.act_window',
            'res_model': 'match.invoice.wizard.payment',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_invoice_id': self.id,
                'default_transaction_amount': match.amount_due if match.match_status == 'partial' else match.amount,
            }
        }

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    transaction_ref = fields.Char(string="Transaction Refrence") 
    effective_date = fields.Date(string='Effective Date')
    bank_reference = fields.Char(string='Bank Reference') 
    cheque_reference = fields.Char(string='Cheque Reference')
    attachment = fields.Binary(string="Upload File")
    attachment_filename = fields.Char("File Name")

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    invoice_id = fields.Many2one('account.move', string="Invoice")
