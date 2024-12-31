from odoo import models, fields, api,_
from odoo.exceptions import UserError
import base64
from odoo.fields import Command
import random


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
        string='Categories',
        domain="[('brand_id', '=', brand_id)]",
         required=True,
        help='Select the Categories associated with the selected brand'
    )

    text_fields = fields.One2many('dynamic.field.text', 'sale_order_id' )
    checkbox_fields = fields.One2many('dynamic.field.checkbox', 'sale_order_id')
    selection_fields = fields.One2many('dynamic.saleorder.selection.key', 'sale_order_id')
    revision_number = fields.Char('')
    revision_number_count = fields.Integer(compute="_compute_revision_number_count",)
    terms_conditions = fields.Text(string='Brand Terms & Conditions')
    bom_id = fields.Many2one('bom.products', string='BOM', help='Select the Bill of Materials')

    @api.onchange('bom_id')
    def _onchange_bom_id(self):
        if self.bom_id:
            self.order_line = [(5, 0, 0)]  
            new_lines = []
            for line in self.bom_id.line_product_ids:
                new_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_uom_qty,
                    'product_uom': line.product_uom.id,
                    'name': line.product_id.name,
                    'price_unit': line.product_id.lst_price,
                }))
            self.order_line = new_lines


    @api.depends('revision_number')
    def _compute_revision_number_count(self):
        for item in self:
            print( self.search_count([('revision_number','=',item.revision_number)]))
            print('ssssssssssssssssssssssssssssssss')
            if item.revision_number:
                item.revision_number_count = self.search_count([('revision_number','=',item.revision_number)])
            else:
                item.revision_number_count = 0

    def action_view_revisions(self):
        self.ensure_one()
        source_orders = self.search([('revision_number','=',self.revision_number)])
        view_tree = self.env.ref('sale.view_quotation_tree_with_onboarding')
        view_from = self.env.ref('sale.view_order_form')
        return {
            'name': _('Revision'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form,tree',
            'domain': [('id', 'in', source_orders.ids)],
            'res_model': 'sale.order',
            'views': [[view_tree.id, "list"],[view_from.id, "form"]],
            'target': 'self'
        }


    def action_revise_order(self):
        for item in self:

            if not item.revision_number:
                revision_number_count = 1
                item.revision_number = item.name
            else:
                revision_number_count = self.search_count([('revision_number', '=', item.revision_number)])

            new_item = item.copy()
            number  = 2 if revision_number_count ==2 else revision_number_count + 1
            new_item.name = item.revision_number+'-'+str(revision_number_count)
            item.action_cancel()

            return {
                'type': 'ir.actions.act_window',
                'name': 'Revised Order',
                'view_mode': 'form',
                'res_model': self._name,  # Use the model name of the current object
                'res_id': new_item.id,  # Pass the ID of the new record
                'target': 'current',  # Open in the current window
            }

    @api.onchange('brand_id')
    def _onchange_text_fields(self):
        for line in self:
            line.text_fields.unlink()
            print('22222222222222222')
            random_number = random.randint(100000, 999999)

            if line.brand_id:
                print( line.brand_id.text_fields.ids)
                print(line.brand_id.checkbox_fields)
                print("00000000000000000000000000000")
                copied_text_fields = []
                checkbox_fields = []
                selection_fields = []
                for item in line.brand_id.text_fields:
                    copied_text_fields.append(item.copy({
                        'sale_order_id': line.id,
                        'brand_id': False  # Clear the brand_id field
                    }).id)
                print(copied_text_fields, "copied_text_fields 11111111111111111111111111----")
                for item in line.brand_id.checkbox_fields:
                    copied_item = item.copy({
                        'sale_order_id': line.id,
                        'brand_id': False  # Clear the brand_id field
                    }).id
                    # copied_item.brand_id , "aaaaaaaaaaaaaaaaaaaaaa new "
                    checkbox_fields.append(copied_item)
                op_key = '00000'
                for item in line.brand_id.selection_fields:
                    options = {}
                    item_sale_item_selection = {'selection_field': item.selection_field,
                    'sale_order_id':line.id}
                    selection_id = self.env['dynamic.saleorder.selection.key'].create(item_sale_item_selection)
                    for value in item.selection_value:
                        print(item.selection_field,"item.selection_field")
                        options = {'key_field_parent':item.selection_field, 'value_field':value.value_field
                        , 'sale_order_no': random_number,'key_field':selection_id.id}
                        print (options,"options")
                        self.env['dynamic.field.selection.values.sale'].create(options)
                    selection_fields.append(selection_id.id)
                print(checkbox_fields ,"checkbox_fields")
                print(selection_fields, "selection_fields")
                line.text_fields = copied_text_fields
                line.checkbox_fields = checkbox_fields #line.brand_id.checkbox_fields.ids
                line.selection_fields = selection_fields #line.brand_id.selection_fields.ids
                return  {'domain': {'text_fields': copied_text_fields, 'checkbox_fields': checkbox_fields,
                                    'selection_fields':selection_fields}}
            else:
                return {'domain': {'text_fields': [],
                                   'checkbox_fields': [],
                                   'selection_fields': []}}



    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()

        values = {
            'ref': self.client_order_ref or '',
            'move_type': 'out_invoice',
            'narration': self.note,
            'currency_id': self.currency_id.id,
            'campaign_id': self.campaign_id.id,
            'medium_id': self.medium_id.id,
            'source_id': self.source_id.id,
            'team_id': self.team_id.id,
            'partner_id': self.partner_invoice_id.id,
            'partner_shipping_id': self.partner_shipping_id.id,
            'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id._get_fiscal_position(self.partner_invoice_id)).id,
            'invoice_origin': self.name,
            'invoice_payment_term_id': self.payment_term_id.id,
            'invoice_user_id': self.user_id.id,
            'payment_reference': self.reference,
            'transaction_ids': [Command.set(self.transaction_ids.ids)],
            'company_id': self.company_id.id,
            'invoice_line_ids': [],
            'user_id': self.user_id.id,
            'brand_id': self.brand_id.id,
            'sku_ids': [(6, 0, self.sku_ids.ids)],  
            'terms_conditions': self.terms_conditions,
        }
        if self.journal_id:
            values['journal_id'] = self.journal_id.id
        return values

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

 
    @api.depends('order_id.brand_id')
    def _compute_filtered_product_ids(self):
        """
        Compute filtered products based on the selected brand and SKU ID.
        """
        for line in self:
            if line.order_id and line.order_id.brand_id and line.order_id.sku_ids:
                sku_ids = line.order_id.sku_ids.ids
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
                line.tax_id = product.tax_id
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
            product_tmpl = self.env['product.product'].browse(vals['filtered_product_id'])
            vals.update({
                'product_id': product_tmpl.id,
                'name': product_tmpl.display_name,
                'price_unit': product_tmpl.list_price,
                'tax_id': [(6, 0, product_tmpl.tax_id.id)],
            })
        return super(SaleOrderLine, self).create(vals)


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
                'taxes_id': [(6, 0, product_tmpl.tax_id.id)],
            })
        return super(SaleOrderLine, self).write(vals)
