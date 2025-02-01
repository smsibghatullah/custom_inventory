from odoo import models, fields, api,_
from odoo.exceptions import UserError
import base64

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    brand_id = fields.Many2one(
        'brand.master', 
        string='Brand',
         required=True,
        help='Select the brand associated with this sale order'
    )

    sku_ids = fields.Many2many(
        'sku.type.master',
        'purchase_sku_rel',
        'product_id',
        string='Categories',
        domain="[('brand_id', '=', brand_id)]",
         required=True,
        help='Select the Categories associated with the selected brand'
    )

    terms_conditions = fields.Text(string='Brand Terms & Conditions')

    def _prepare_invoice(self):
        """Prepare the dict of values to create the new invoice for a purchase order.
        """
        self.ensure_one()
        move_type = self._context.get('default_move_type', 'in_invoice')

        partner_invoice = self.env['res.partner'].browse(self.partner_id.address_get(['invoice'])['invoice'])
        partner_bank_id = self.partner_id.commercial_partner_id.bank_ids.filtered_domain(['|', ('company_id', '=', False), ('company_id', '=', self.company_id.id)])[:1]

        invoice_vals = {
            'ref': self.partner_ref or '',
            'move_type': move_type,
            'narration': self.notes,
            'currency_id': self.currency_id.id,
            'partner_id': partner_invoice.id,
            'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id._get_fiscal_position(partner_invoice)).id,
            'payment_reference': self.partner_ref or '',
            'partner_bank_id': partner_bank_id.id,
            'invoice_origin': self.name,
            'invoice_payment_term_id': self.payment_term_id.id,
            'brand_id': self.brand_id.id,
            'sku_ids': [(6, 0, self.sku_ids.ids)],
            'terms_conditions': self.brand_id.terms_conditions_invoice,
            'invoice_line_ids': [],
            'company_id': self.company_id.id,
        }
        return invoice_vals

    @api.onchange('brand_id')
    def _onchange_brand_id(self):
        if self.brand_id:
            self.sku_ids = False
            self.terms_conditions = self.brand_id.terms_conditions

    def action_send_report_email(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Send Email',
            'res_model': 'purchase.order.email.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_purchase_order_id': self.id,
                'default_recipient_email': self.partner_id.email,
                'default_subject': f'Purchase Order {self.name}',
            },
        }


class PurchaseOrderEmailWizard(models.TransientModel):
    _name = 'purchase.order.email.wizard'
    _description = 'Purchase Order Email Wizard'

    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order', required=True, readonly=True)
    recipient_email = fields.Char(string='Recipient Email', required=True)
    subject = fields.Char(string='Subject', required=True, default='Purchase Order Report')

    def action_send_email(self):
        self.ensure_one()

        purchase_order = self.env['purchase.order'].browse(self.env.context.get('active_id'))
        if not purchase_order:
            raise UserError(_("No Purchase Order found to generate the email."))

        report_name = 'purchase.report_purchaseorder'

        try:
            pdf_content, content_type = self.env['ir.actions.report']._render_qweb_pdf(
                report_name, [purchase_order.id]
            )

            pdf_base64 = base64.b64encode(pdf_content)
            attachment = self.env['ir.attachment'].create({
                'name': f"{purchase_order.name}.pdf",
                'type': 'binary',
                'datas': pdf_base64,
                'res_model': 'purchase.order',
                'res_id': purchase_order.id,
                'mimetype': 'application/pdf',
            })
            from_email = purchase_order.brand_id.po_email
            if not from_email:
                raise UserError(_("No Purchase Order email is set for the selected brand."))
            mail_values = {
                'subject': self.subject or f"Purchase Order {purchase_order.name}",
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


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

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

    @api.depends('order_id.sku_ids')
    def _compute_product_sku_id(self):
        """
        Compute the product template based on sku_ids from the order.
        This is just an example; this method may also involve other logic.
        """
        for line in self:
                if line.order_id and line.order_id.sku_ids:
                    line.sku_ids = line.order_id.sku_ids.ids
                else:
                    sku_ids = self.env['sku.type.master'].search([]) 
                    line.sku_ids = sku_ids

    @api.onchange('product_id')
    def _compute_product_template_id(self):
        for line in self:
                if line.order_id and line.order_id.sku_ids:
                    line.sku_ids = line.order_id.sku_ids.ids
                else:
                    sku_ids = self.env['sku.type.master'].search([]) 
                    line.sku_ids = sku_ids
            
    