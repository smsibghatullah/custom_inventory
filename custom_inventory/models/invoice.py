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

    @api.onchange('brand_id')
    def _onchange_brand_id(self):
        if self.brand_id:
            self.sku_ids = False

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

    filtered_product_id = fields.Many2one(
        string='Product',
        comodel_name='product.product',
        compute='_compute_filtered_product_id',
        readonly=False,
        domain="[('id', 'in', filtered_product_ids)]",
    )

    filtered_product_ids = fields.Many2many(
        comodel_name="product.product",
        string='.',
        compute="_compute_filtered_product_ids",
        store=False,
    )

    @api.depends('move_id.brand_id')
    def _compute_filtered_product_ids(self):
        """
        Compute filtered products based on the selected brand and SKU ID.
        """
        for line in self:
            if line.move_id and line.move_id.brand_id and line.move_id.sku_ids:
                sku_ids = line.move_id.sku_ids.ids
                matching_templates = self.env['product.template'].search([
                    ('sku_ids', 'in', sku_ids)
                ])
                matching_products = self.env['product.product'].search([
                    ('product_tmpl_id', 'in', matching_templates.ids)
                ])
                line.filtered_product_ids = matching_products
            else:
                line.filtered_product_ids = self.env['product.product']


    @api.depends('filtered_product_ids')
    def _compute_filtered_product_id(self):
        """
        Set `filtered_product_id` if it matches the filtered products.
        """
        for line in self:
            if line.filtered_product_ids and line.product_id in line.filtered_product_ids:
                line.filtered_product_id = line.product_id.id
            else:
                line.filtered_product_id = False

    @api.onchange('filtered_product_id')
    def _onchange_filtered_product_id(self):
        """
        Update sale order line details when filtered product changes.
        """
        for line in self:
            if line.filtered_product_id:
                product = line.filtered_product_id
                line.product_id = product
                line.name = product.display_name
                line.price_unit = product.list_price
                line.tax_ids = product.taxes_id
            else:
                line.product_id = False
                line.name = False
                line.price_unit = 0.0
                line.tax_ids = [(5, 0, 0)]

    @api.model
    def create(self, vals):
        """
        Ensure `filtered_product_id` updates `product_id` and other fields.
        """
        if 'filtered_product_id' in vals and vals['filtered_product_id']:
            product_tmpl = self.env['product.product'].browse(vals['filtered_product_id'])
            vals.update({
                'product_id': product_tmpl.id,
                'name': product_tmpl.display_name,
                'price_unit': product_tmpl.list_price,
                'tax_ids': [(6, 0, product_tmpl.taxes_id.ids)],
            })
        return super(AccountMoveLine, self).create(vals)

    def write(self, vals):
        """
        Ensure `filtered_product_id` updates `product_id` and other fields.
        """
        if 'filtered_product_id' in vals and vals['filtered_product_id']:
            product_tmpl = self.env['product.template'].browse(vals['filtered_product_id'])
            vals.update({
                'product_id': product_tmpl.id,
                'name': product_tmpl.display_name,
                'price_unit': product_tmpl.list_price,
                'tax_ids': [(6, 0, product_tmpl.taxes_id.ids)],
            })
        return super(AccountMoveLine, self).write(vals)
