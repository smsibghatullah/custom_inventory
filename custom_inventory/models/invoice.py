from odoo import models, fields, api,_
from odoo.exceptions import UserError
import base64

class AccountMove(models.Model):
    _inherit = 'account.move'

    brand_id = fields.Many2one(
        'brand.master', 
        string='Brand',
         required=True,
        help='Select the brand associated with this sale order'
    )

    sku_ids = fields.Many2many(
        'sku.type.master',
        'account_sku_rel',
        'product_id',
        string='Categories',
        domain="[('brand_id', '=', brand_id)]",
         required=True,
        help='Select the Categories associated with the selected brand'
    )
    terms_conditions = fields.Text(string='Brand Terms & Conditions')
    bom_id = fields.Many2one('bom.products', string='BOM', help='Select the Bill of Materials')

    @api.onchange('bom_id')
    def _onchange_bom_id(self):
        if self.bom_id:
            self.invoice_line_ids = [(5, 0, 0)]  
            new_lines = []
            for line in self.bom_id.line_product_ids:
                 new_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'quantity': line.product_uom_qty,
                    'name': line.product_id.name,
                    'price_unit': line.product_id.lst_price,
                }))
            
            self.invoice_line_ids = new_lines

    @api.onchange('brand_id')
    def _onchange_brand_id(self):
        if self.brand_id:
            self.sku_ids = False
            self.terms_conditions = self.brand_id.terms_conditions_invoice

    def action_send_report_email(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Send Email',
            'res_model': 'invoice.order.email.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_invoice_order_id': self.id,
                'default_recipient_email': self.partner_id.email,
                'default_subject': f'Invoice {self.name}',
            },
        }


class InvoiceOrderEmailWizard(models.TransientModel):
    _name = 'invoice.order.email.wizard'
    _description = 'Invoice Order Email Wizard'

    invoice_order_id = fields.Many2one('account.move', string='Invoice', required=True, readonly=True)
    recipient_email = fields.Char(string='Recipient Email', required=True)
    subject = fields.Char(string='Subject', required=True, default='Purchase Order Report')

    def action_send_email(self):
        self.ensure_one()

        invoice = self.env['account.move'].browse(self.env.context.get('active_id'))
        if not invoice:
            raise UserError(_("No Invoice found to generate the email."))

        report_name = 'account.report_invoice'

        try:
            pdf_content, content_type = self.env['ir.actions.report']._render_qweb_pdf(
                report_name, [invoice.id]
            )

            pdf_base64 = base64.b64encode(pdf_content)
            attachment = self.env['ir.attachment'].create({
                'name': f"{invoice.name}.pdf",
                'type': 'binary',
                'datas': pdf_base64,
                'res_model': 'account.move',
                'res_id': invoice.id,
                'mimetype': 'application/pdf',
            })
            from_email = invoice.brand_id.inv_email
            if not from_email:
                raise UserError(_("No Invoice email is set for the selected brand."))
            mail_values = {
                'subject': self.subject or f"Purchase Order {invoice.name}",
                'body_html': _('Please find attached your Purchase Order.'),
                'email_from': from_email,
                'email_to': self.recipient_email,
                'attachment_ids': [(6, 0, [attachment.id])],
            }
            mail = self.env['mail.mail'].create(mail_values)
            mail.send()

        except Exception as e:
            raise UserError(_("An error occurred while generating the PDF: %s") % str(e))

        return {'type': 'ir.actions.act_window_close'}



class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    sku_ids = fields.Many2many(
        'sku.type.master',
        'purchase_line_sku_rel',
        'product_id',
        'sku_id',
        string=' ',
        compute='_compute_product_sku_id',
        required=True,
        help='Select the Categories associated with the selected brand'
    )

    @api.depends('move_id.sku_ids')
    def _compute_product_sku_id(self):
        """
        Compute the product template based on sku_ids from the order.
        This is just an example; this method may also involve other logic.
        """
        for line in self:
            for line in self:
                if not line.move_id.bom_id:
                    if line.move_id and line.move_id.sku_ids:
                        self.sku_ids = line.move_id.sku_ids.ids
                else:
                    sku_ids = self.env['sku.type.master'].search([]) 
                    line.sku_ids = sku_ids
            
    
            

    @api.onchange('product_id')
    def _compute_product_template_id(self):
        for line in self:
            if not line.move_id.bom_id:
                if line.move_id and line.move_id.sku_ids:
                    self.sku_ids = line.move_id.sku_ids.ids
            else:
                sku_ids = self.env['sku.type.master'].search([]) 
                line.sku_ids = sku_ids
    
            
    