from odoo import models, fields, api,_
from odoo.exceptions import UserError
import base64


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    brand_id = fields.Many2one(
        'brand.master', 
        string='Brand',
         required=True,
        help='Select the brand associated with this sale order'
    )

    sku_ids = fields.Many2many(
        'sku.type.master',
        'sale_sku_rel',
        'product_id',
        'sku_id',
        string='SKU',
        domain="[('brand_id', '=', brand_id)]",
         required=True,
        help='Select the SKU associated with the selected brand'
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
            'res_model': 'sale.order.email.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_order_id': self.id,
                'default_recipient_email': self.partner_id.email,
                'default_subject': f'Sale Order {self.name}',
            },
        }

class SaleOrderEmailWizard(models.TransientModel):
    _name = 'sale.order.email.wizard'
    _description = 'Sale Order Email Wizard'

    sale_order_id = fields.Many2one('sale.order', string='Sale Order', required=True, readonly=True)
    recipient_email = fields.Char(string='Recipient Email', required=True)
    subject = fields.Char(string='Subject', required=True, default='Sale Order Report')
   

    def action_send_email(self):
        self.ensure_one()

        sale_order = self.env['sale.order'].browse(self.env.context.get('active_id'))
        if not sale_order:
            raise UserError(_("No Sale Order found to generate the email."))

        report_name = 'sale.report_saleorder'

        try:
            pdf_content, content_type = self.env['ir.actions.report']._render_qweb_pdf(
                report_name, [sale_order.id]
            )

            pdf_base64 = base64.b64encode(pdf_content)
            attachment = self.env['ir.attachment'].create({
                'name': f"{sale_order.name}.pdf",
                'type': 'binary',
                'datas': pdf_base64,
                'res_model': 'sale.order',
                'res_id': sale_order.id,
                'mimetype': 'application/pdf',
            })
            from_email = sale_order.brand_id.so_email
            if not from_email:
                raise UserError(_("No Sale Order email is set for the selected brand."))
            mail_values = {
                'subject': self.subject or f"Sale Order {sale_order.name}",
                'body_html': _('Please find attached your Sale Order.'),
                'email_from': from_email, 
                'email_to': self.recipient_email,
                'attachment_ids': [(6, 0, [attachment.id])],
            }
            mail = self.env['mail.mail'].create(mail_values)
            mail.send()

        except Exception as e:
            raise UserError(_("An error occurred while generating the PDF: %s") % str(e))

        return {'type': 'ir.actions.act_window_close'}


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    filtered_product_id = fields.Many2one(
        string='Product',
        comodel_name='product.template',
        compute='_compute_filtered_product_id',
        readonly=False,
        domain="[('id', 'in', filtered_product_ids)]",
    )

    filtered_product_ids = fields.Many2many(
        comodel_name="product.template",
        string='.',
        compute="_compute_filtered_product_ids",
        store=False,
    )

    @api.depends('order_id.brand_id')
    def _compute_filtered_product_ids(self):
         for line in self:
            if line.order_id and line.order_id.brand_id:
                brand_id = line.order_id.brand_id.id
                sku_ids = line.order_id.sku_ids.ids  
                matching_products = self.env['product.template'].search([
                    ('sku_ids', 'in', sku_ids),  
                ])
                line.filtered_product_ids = matching_products
            else:
                line.filtered_product_ids = self.env['product.template']


    @api.depends('filtered_product_ids')
    def _compute_filtered_product_id(self):
        """
        Set `filtered_product_id` if it matches the filtered products.
        """
        for line in self:
            if line.filtered_product_ids and line.product_id.product_tmpl_id in line.filtered_product_ids:
                line.filtered_product_id = line.product_id.product_tmpl_id
            else:
                line.filtered_product_id = False


    @api.onchange('filtered_product_id')
    def _onchange_filtered_product_id(self):
        """
        Update sale order line details when filtered product changes.
        """
        for line in self:
            if line.filtered_product_id:
                product = line.filtered_product_id.product_variant_id
                line.product_id = product
                line.name = product.display_name
                line.price_unit = product.list_price
                line.tax_id = product.taxes_id
            else:
                line.product_id = False
                line.name = False
                line.price_unit = 0.0
                line.tax_id = [(5, 0, 0)]


    @api.model
    def create(self, vals):
        """
        Ensure `filtered_product_id` updates `product_id` and other fields.
        """
        if 'filtered_product_id' in vals and vals['filtered_product_id']:
            product_tmpl = self.env['product.template'].browse(vals['filtered_product_id'])
            product_variant = product_tmpl.product_variant_id
            vals.update({
                'product_id': product_variant.id,
                'name': product_variant.display_name,
                'price_unit': product_variant.list_price,
                'tax_id': [(6, 0, product_variant.taxes_id.ids)],
            })
        return super(SaleOrderLine, self).create(vals)


    def write(self, vals):
        """
        Ensure `filtered_product_id` updates `product_id` and other fields.
        """
        if 'filtered_product_id' in vals and vals['filtered_product_id']:
            product_tmpl = self.env['product.template'].browse(vals['filtered_product_id'])
            product_variant = product_tmpl.product_variant_id
            vals.update({
                'product_id': product_variant.id,
                'name': product_variant.display_name,
                'price_unit': product_variant.list_price,
                'tax_id': [(6, 0, product_variant.taxes_id.ids)],
            })
        return super(SaleOrderLine, self).write(vals)
