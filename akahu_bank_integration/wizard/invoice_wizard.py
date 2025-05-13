from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime

class MatchInvoiceWizard(models.TransientModel):
    _name = 'match.invoice.wizard'
    _description = 'Match Transaction with Invoices'

    transaction_ref = fields.Char('Transaction Reference')
    invoice_line_ids = fields.One2many('match.invoice.wizard.line', 'wizard_id', string='Invoices')
    attachment = fields.Binary(string="Upload File")
    attachment_filename = fields.Char("File Name")

    def action_create_payments(self):
        selected_invoices = self.invoice_line_ids.filtered(lambda l: l.selected).mapped('invoice_id')
        invoices_to_pay = selected_invoices.filtered(lambda inv: inv.state == 'posted' and inv.payment_state != 'paid')

        if not invoices_to_pay:
            raise UserError("No valid invoices or bills to pay.")

        partners = invoices_to_pay.mapped('partner_id')
        if len(partners) > 1:
            raise UserError("All selected invoices/bills must belong to the same partner.")
        partner = partners[0]

        match = self.env['akahu.transaction'].search([('reference', '=', self.transaction_ref)], limit=1)
        if not match:
            raise UserError("No transaction found with reference: %s" % self.transaction_ref)

        journal = self.env['account.journal'].search([
            ('type', '=', 'bank'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        if not journal:
            raise UserError("Bank journal not found.")
        if not journal.inbound_payment_method_line_ids:
            raise UserError("The selected journal has no inbound payment methods configured.")

        payment_method = journal.inbound_payment_method_line_ids[0]
        total_amount = match.amount
        total_invoice_amount = sum(invoices_to_pay.mapped('amount_residual'))
        print(total_invoice_amount,"op==================================<><><><<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
        payment_amount = min(
            abs(match.amount_due if match.match_status == 'partial' else total_amount),
            abs(total_invoice_amount)
        )

        if invoices_to_pay[0].move_type in ['in_invoice']:
                print('1==========================================')
                payment_vals = {
                    'payment_type': 'inbound' if match.amount_due > 0 else 'outbound',
                    'partner_type': 'supplier',
                    'partner_id': partner.id,
                    'amount': payment_amount,
                    'date': fields.Date.today(),
                    'journal_id': journal.id,
                    'payment_method_line_id': payment_method.id,
                    'ref': match.reference,
                }
                account_type = 'liability_payable'

        elif invoices_to_pay[0].move_type in ['out_refund']:
            print('2==========================================')            
            payment_vals = {
                'payment_type': 'outbound', 
                'partner_type': 'customer',
                'partner_id': partner.id,
                'amount': payment_amount,
                'date': fields.Date.today(),
                'journal_id': journal.id,
                'payment_method_line_id': payment_method.id,
                'ref': match.reference,
            }
            account_type = 'asset_receivable'

        elif invoices_to_pay[0].move_type in ['out_invoice']:
            print('3==========================================')
            payment_vals = {
                'payment_type': 'inbound' if match.amount_due > 0 else 'outbound',
                'partner_type': 'customer',
                'partner_id': partner.id,
                'amount': payment_amount,
                'date': fields.Date.today(),
                'journal_id': journal.id,
                'payment_method_line_id': payment_method.id,
                'ref': match.reference,
            }
            account_type = 'asset_receivable'

        elif invoices_to_pay[0].move_type in ['in_refund']:
            print('4==================================')
            payment_vals = {
                'payment_type': 'inbound' if match.amount_due > 0 else 'outbound', 
                'partner_type': 'supplier',
                'partner_id': partner.id,
                'amount': payment_amount,
                'date': fields.Date.today(),
                'journal_id': journal.id,
                'payment_method_line_id': payment_method.id,
                'ref': match.reference,
            }
            account_type = 'liability_payable'

        else:
            print('5==========================================')
            payment_vals = {
                'payment_type': 'inbound' if match.amount_due > 0 else 'outbound',
                'partner_type': 'customer',
                'partner_id': partner.id,
                'amount': payment_amount,
                'date': fields.Date.today(),
                'journal_id': journal.id,
                'payment_method_line_id': payment_method.id,
                'ref': match.reference,
            }
            account_type = 'asset_receivable'


        payment = self.env['account.payment'].sudo().create(payment_vals)
        payment.action_post()

        payment_lines = payment.move_id.line_ids.filtered(lambda l: l.account_id.account_type == account_type)
        invoice_lines = invoices_to_pay.mapped('line_ids').filtered(lambda l: l.account_id.account_type == account_type)
        (payment_lines + invoice_lines).reconcile()

        payment.attachment = self.attachment
        payment.reconciled_invoice_ids = invoices_to_pay.ids
        payment.reconciled_invoices_count = len(invoices_to_pay.ids)
        payment.duplicated_ref_ids = invoices_to_pay.ids
        payment.reconciled_bill_ids = invoices_to_pay.ids
        payment.reconciled_bills_count = len(invoices_to_pay.ids)

        invoices_to_pay.write({
            'transaction_ref': match.name,
            'reference': match.reference,
        })

        
        match.amount_paid += total_invoice_amount if match.amount >= 0 else -total_invoice_amount
        match.amount_due = match.amount - match.amount_paid

        if match.amount >= 0 and match.amount_due < 0:
            match.amount_due = 0.0
        elif match.amount < 0 and match.amount_due > 0:
            match.amount_due = 0.0

        if abs(match.amount_due) < 0.0001:
            match.match_status = 'matched'
            match.amount_due = 0.0
        else:
            match.match_status = 'partial'

        payment.write({'transaction_ref': match.name})
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



