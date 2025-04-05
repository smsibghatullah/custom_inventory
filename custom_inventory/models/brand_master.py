from odoo import models, fields, api,_
from odoo.exceptions import UserError
import base64

class BrandMaster(models.Model):
    _name = 'brand.master'
    _description = 'Brand Master'

    name = fields.Char(string='Brand', required=True)
    logo = fields.Binary()
    printable_formats = fields.Char(string='Printable Formats')  
    so_email = fields.Char(string='Sale Order Email', required=True)
    po_email = fields.Char(string='Purchase Order Email')
    inv_email = fields.Char(string='Invoice Email')
    terms_conditions = fields.Text(string='Terms & Conditions')
    terms_conditions_invoice = fields.Text(string='Terms & Conditions')
    terms_conditions_purchase = fields.Text(string='Terms & Conditions')
    bank_account_details = fields.Text(string='Bank Account Details')
    address = fields.Text(string='Address')
    text_fields = fields.One2many('dynamic.field.text', 'brand_id', string='Text Fields')
    checkbox_fields = fields.One2many('dynamic.field.checkbox', 'brand_id', string='Checkbox Fields')
    selection_fields = fields.One2many('dynamic.field.selection.key', 'brand_id', string='Selection Fields')
    is_tax_show = fields.Boolean(
        string="Is Tax",
        default=False,
        help="Indicates whether this line represents a tax-related item."
    )
    is_tag_show = fields.Boolean(
        string="Is Tag",
        default=False,
        help="Indicates whether this line represents a tag-related item."
    )
    company_id = fields.Many2one('res.company', string="Company")
    purchase_text_fields = fields.One2many('purchase.dynamic.field.text', 'brand_id', string='Purchase Text Fields')
    purchase_checkbox_fields = fields.One2many('purchase.dynamic.field.checkbox', 'brand_id', string='Purchase Checkbox Fields')
    purchase_selection_fields = fields.One2many('purchase.dynamic.field.selection.key', 'brand_id', string='Purchase Selection Fields')
    mail_sale_quotation_template_id = fields.Many2one(
        comodel_name='mail.template',
        string="Use Sale Quotation template",
        domain="[('model', '=', 'sale.order')]",
    )
    mail_sale_template_id = fields.Many2one(
        comodel_name='mail.template',
        string="Use Sale Order template",
        domain="[('model', '=', 'sale.order')]",
    )
    mail_purchase_quotation_template_id = fields.Many2one(
        comodel_name='mail.template',
        string="Use RFQ template",
        domain="[('model', '=', 'purchase.order')]",
    )
    mail_purchase_template_id = fields.Many2one(
        comodel_name='mail.template',
        string="Use Purchase Order template",
        domain="[('model', '=', 'purchase.order')]",
    )
    mail_invoice_template_id = fields.Many2one(
        comodel_name='mail.template',
        string="Use Invoice template",
        domain="[('model', '=', 'account.move')]",
    )



class ProductProduct(models.Model):
    _inherit = 'product.product'

    brand_ids = fields.Many2many(
        'brand.master',
        'product_brand_rel_product',
        'product_id',
        'brand_id',
        string='Brands',
    )
    is_brand_matched = fields.Boolean(string='Is Brand Matched', default=False)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    category_ids = fields.Many2many(
        'sku.type.master',
        'product_category_rel',
        'product_id',
        'category_id',
        string='Categories',
        required=True
    )
    is_brand_matched = fields.Boolean(string='Is Brand Matched', default=False)
    available_sku_category_ids = fields.Many2many(
        'sku.type.master',
        compute="_compute_available_categories",
    )
  
    @api.depends("category_ids")
    def _compute_available_categories(self):
        for record in self:
            record.available_sku_category_ids = self.env.user.category_ids

    @api.depends_context('company')
    @api.depends('product_variant_ids.standard_price')
    def _compute_standard_price(self):
        for record in self:
            previous_price = record.standard_price
            record._compute_template_field_from_variant_field('standard_price')
            if record.standard_price == 0 and previous_price:
                record.standard_price = previous_price


   

