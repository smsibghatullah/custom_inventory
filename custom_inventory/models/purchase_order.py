from unicodedata import category

from odoo import models, fields, api,_
from odoo.exceptions import UserError,ValidationError
import base64
from odoo.fields import Command
import random
from collections import defaultdict

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    brand_id = fields.Many2one(
        'brand.master', 
        string='Brand',
         required=True,
          domain="[('company_id', '=', company_id)]",
        help='Select the brand associated with this sale order'
    )



    tag_ids = fields.One2many(
        'crm.tag',  
        'purchase_id', 
        string='Tags',
        help='Select the brands associated with this company'
    )

    terms_conditions = fields.Text(string='Brand Terms & Conditions')
    is_tag_access = fields.Boolean(compute="_compute_tag_access")
    has_tag_required = fields.Boolean(compute="_compute_has_tag_required", store=True)
    text_fields = fields.One2many('purchase.dynamic.field.text', 'purchase_order_id', compute="_compute_text_field", inverse="_inverse_text_field", store=True )
    checkbox_fields = fields.One2many('purchase.dynamic.field.checkbox', 'purchase_order_id', compute="_compute_checkbox_field", inverse="_inverse_checkbox_field", store=True)
    selection_fields = fields.One2many('purchase.dynamic.purchaseorder.selection.key', 'purchase_order_id', compute="_compute_selection_field", inverse="_inverse_selection_field", store=True)
    has_text_fields = fields.Boolean(compute="_compute_has_text_fields", store=True)
    has_checkbox_fields = fields.Boolean(compute="_compute_has_checkbox_fields", store=True)
    has_selection_fields = fields.Boolean(compute="_compute_has_selection_fields", store=True)
    available_tag_ids = fields.Many2many(
        'crm.tag',
        compute="_compute_available_tags",
    )
    available_category_ids = fields.Many2many(
        'sku.type.master',
        compute="_compute_available_categories",
    )
    category_ids = fields.Many2many(
        'sku.type.master',
        'purchase_category_rel',
        'product_id',
        string='Categories',
        domain="[('brand_id', '=', brand_id),('id', 'in', available_category_ids)]",
         required=True,
        help='Select the Categories associated with the selected brand'
    )
    @api.depends("tag_ids")
    def _compute_available_tags(self):
        for record in self:
            record.available_tag_ids = self.env.user.tag_ids
            print(record.available_tag_ids,"ppppppppppppppppppppppppmubeenpssssssssssssssssssssssssss")
    @api.depends("category_ids")
    def _compute_available_categories(self):
        for record in self:
            record.available_category_ids = self.env.user.category_ids
            print(record.available_tag_ids,"ppppppppppppppppppppppppmubeenpssssssssssssssssssssssssss")


    @api.model
    def create(self, vals):
        order = super(PurchaseOrder, self).create(vals)
        print(order.amount_total,"mmmmmmmmmmmmmmmmmmmmmmmmmm")
        for item in order.text_fields:
                if item.validation_check and not item.text_value:
                    raise ValidationError(f"The field '{item.text_field}' requires a value.")
        if order.amount_total == 0:
                raise ValidationError("The Purchase Order total amount cannot be zero.")
        
        return order

    @api.model
    def write(self, vals):
        result = super(PurchaseOrder, self).write(vals)
        print(self.amount_total,"mmmmmmmmccccmmmmmmmmmmmmmmmmmm")
        for order in self:
            for item in order.text_fields:
                if item.validation_check and not item.text_value:
                    raise ValidationError(f"The field '{item.text_field}' requires a value.")
            if order.amount_total == 0:
                raise ValidationError("The Purchase Order total amount cannot be zero.")
        
        return result

    def _inverse_text_field(self):
        for line in self:
            for item in line.text_fields:
                # Update the sale_order_id on the corresponding text field
                item.purchase_order_id = line.id

    def _inverse_checkbox_field(self):
        for line in self:
            for item in line.checkbox_fields:
                # Update the purchase_order_id on the corresponding text field
                item.purchase_order_id = line.id

    def _inverse_selection_field(self):
        for line in self:
            for item in line.selection_fields:
                # Update the purchase_order_id on the corresponding text field
                item.purchase_order_id = line.id

    @api.depends('text_fields')
    def _compute_has_text_fields(self):
        for record in self:
            record.has_text_fields = bool(record.text_fields)

    @api.depends('checkbox_fields')
    def _compute_has_checkbox_fields(self):
        for record in self:
            record.has_checkbox_fields = bool(record.checkbox_fields)

    @api.depends('selection_fields')
    def _compute_has_selection_fields(self):
        for record in self:
            record.has_selection_fields = bool(record.selection_fields)


    @api.depends("brand_id", "brand_id.is_tag_show")
    def _compute_has_tag_required(self):
        for record in self:
            record.has_tag_required = bool(record.brand_id.is_tag_show)

    @api.depends("brand_id")
    def _compute_tag_access(self):
        for record in self:
            record.is_tag_access = record.brand_id.is_tag_show if record.brand_id else False


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
            'category_ids': [(6, 0, self.category_ids.ids)],
            'terms_conditions': self.brand_id.terms_conditions_invoice,
            'invoice_line_ids': [],
            'company_id': self.company_id.id,
            'tag_ids':[(6, 0, self.tag_ids.ids)],
        }
        return invoice_vals

    @api.onchange('brand_id')
    def _onchange_brand_id(self):
        if self.brand_id:
            self.category_ids = False
            self.order_line  = [(6, 0, [])]
            self.terms_conditions = self.brand_id.terms_conditions_purchase

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

    @api.depends('brand_id')
    def _compute_text_field(self):
        for line in self:
            if line.brand_id:
                copied_text_fields = []
                if line.brand_id.purchase_text_fields:
                    for item in line.brand_id.purchase_text_fields:
                        copied_item = item.copy({
                            'purchase_order_id': line.id,
                            'brand_id': False
                        })
                        copied_text_fields.append(copied_item.id)
                line.text_fields = [(6, 0, copied_text_fields)]
            else:
                line.text_fields = [(5, 0, 0)]
                line.category_ids  = [(6, 0, [])]

    @api.depends('brand_id')
    def _compute_checkbox_field(self):
        for line in self:
            if line.brand_id:
                copied_checkbox_fields = []

                for item in line.brand_id.purchase_checkbox_fields:
                    copied_checkbox_fields.append(item.copy({
                        'purchase_order_id': line.id,
                        'brand_id': False  # Clear the brand_id field
                    }).id)
                line.checkbox_fields = [(6, 0, copied_checkbox_fields)]
                # line.sku_ids  = [(6, 0, [])]



    @api.depends('brand_id')
    def _compute_selection_field(self):
        selection_fields = []
        random_number = random.randint(100000, 999999)
        for line in self:
            if line.brand_id:
                for item in line.brand_id.purchase_selection_fields:
                    options = {}
                    if line.id:
                        selection_id = self.env['purchase.dynamic.purchaseorder.selection.key'].search([('purchase_order_id','=',line.id)])
                        if not selection_id:
                            item_sale_item_selection = {'selection_field': item.selection_field,
                                                        'purchase_order_id': line.id,'sale_random_key': random_number}
                            selection_id = self.env['purchase.dynamic.purchaseorder.selection.key'].create(item_sale_item_selection)
                    else:
                        item_sale_item_selection = {'selection_field': item.selection_field,
                        'purchase_order_id':line.id}
                        selection_id = self.env['purchase.dynamic.purchaseorder.selection.key'].create(item_sale_item_selection)
                    # selection_value = self.env['dynamic.field.selection.values.sale'].search([('sale_random_key','=',selection_id.random_number)])
                    # if selection_value:
                    for value in item.selection_value:
                       options = {
                        'value_field': value.value_field,
                        'key_field': selection_id.id,
                        'key_field_parent': item.selection_field  
                        }
                      
                       new_option = self.env['purchase.dynamic.field.selection.values.purchase'].create(options)
                    
                    if not selection_id.selected_value:
                        selection_id.selected_value = new_option
                    selection_fields.append(selection_id.id)
            line.selection_fields = [(6, 0, selection_fields)]


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

    category_ids = fields.Many2many(
        'sku.type.master',
        'purchase_line_category_rel',
        'product_id',
        'category_id',
        string=' ',
        compute='_compute_product_sku_id',
        required=True,
        help='Select the Categories associated with the selected brand'
    )

    @api.depends('order_id.category_ids')
    def _compute_product_sku_id(self):
        """
        Compute the product template based on sku_ids from the order.
        This is just an example; this method may also involve other logic.
        """
        for line in self:
                if line.order_id and line.order_id.category_ids:
                    line.category_ids = line.order_id.category_ids.ids
                else:
                    category_ids = self.env['sku.type.master'].search([]) 
                    line.category_ids = category_ids

    @api.onchange('product_id')
    def _compute_product_template_id(self):
        for line in self:
                if line.order_id and line.order_id.category_ids:
                    line.category_ids = line.order_id.category_ids.ids
                else:
                    category_ids = self.env['sku.type.master'].search([]) 
                    line.category_ids = category_ids
            
    