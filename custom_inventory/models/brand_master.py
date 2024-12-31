from odoo import models, fields, api,_
from odoo.exceptions import UserError
import base64

class BrandMaster(models.Model):
    _name = 'brand.master'
    _description = 'Brand Master'

    name = fields.Char(string='Brand', required=True)
    logo = fields.Binary(string='Logo')
    printable_formats = fields.Char(string='Printable Formats')  
    so_email = fields.Char(string='Sale Order Email', required=True)
    po_email = fields.Char(string='Purchase Order Email')
    inv_email = fields.Char(string='Invoice Email')
    terms_conditions = fields.Text(string='Terms & Conditions')
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

    sku_ids = fields.Many2many(
        'sku.type.master',
        'product_sku_rel',
        'product_id',
        'sku_id',
        string='Categories',
        required=True
    )
    is_brand_matched = fields.Boolean(string='Is Brand Matched', default=False)

   

