
from odoo import models, fields, api

class InvoiceAttachmentWizard(models.TransientModel):
    _name = 'invoice.attachment.wizard'
    _description = 'Invoice Attachments Viewer'

    invoice_id = fields.Many2one('account.move', string="Invoice")
    attachment_ids = fields.Many2many('ir.attachment', string="Attachments")

