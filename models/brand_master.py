from odoo import models, fields, api

class BrandMaster(models.Model):
    _name = 'brand.master'
    _description = 'Brand Master'

    name = fields.Char(string='Brand', required=True)
    logo = fields.Binary(string='Logo')
    printable_formats = fields.Char(string='Printable Formats')  
    email_smtp_settings = fields.Char(string='Email')
    terms_conditions = fields.Text(string='Terms & Conditions')
    bank_account_details = fields.Char(string='Bank Account Details')
    address = fields.Text(string='Address') 

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




# sale order work start

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    brand_id = fields.Many2one(
        'brand.master', 
        string='Brand',
        help='Select the brand associated with this sale order'
    )


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    sku_ids = fields.Many2many(
        'sku.type.master',
        'product_sku_rel',
        'product_id',
        'sku_id',
        string='SKUs',
    )
    is_brand_matched = fields.Boolean(string='Is Brand Matched', default=False)

   

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
        """
        Compute filtered products based on the selected brand in the sale order.
        """
        for line in self:
            if line.order_id and line.order_id.brand_id:
                brand_id = line.order_id.brand_id.id
                matching_products = self.env['product.template'].search([
                    ('sku_ids.brand_id', '=', brand_id),
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

# sale order work end


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    brand_id = fields.Many2one(
        'brand.master', 
        string='Brand',
        help='Select the brand associated with this purchase order'
    )

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    is_brand_matched = fields.Boolean(
        string='Is Brand Matched', 
        compute='_compute_is_brand_matched', 
        store=False
    )

    filtered_product_id = fields.Many2one(
        'product.template',
        string='Product',
        domain="[('is_brand_matched', '=', True)]",
    )

    @api.onchange('filtered_product_id')
    def _compute_is_brand_matched(self):
        """
        Compute if the product matches the selected brand in the purchase order.
        """
        for line in self:
            if line.order_id and line.order_id.brand_id:
                brand_id = line.order_id.brand_id.id
                matching_products = self.env['product.template'].search([
                    ('brand_ids', 'in', brand_id)
                ])
                matching_product_ids = matching_products.ids
            else:
                matching_product_ids = []
            all_products = self.env['product.template'].search([])
            for product in all_products:
                product.is_brand_matched = product.id in matching_product_ids

class AccountMove(models.Model):
    _inherit = 'account.move'

    brand_id = fields.Many2one(
        'brand.master', 
        string='Brand',
        help='Select the brand associated with this invoice'
    )

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_brand_matched = fields.Boolean(
        string='Is Brand Matched', 
        compute='_compute_is_brand_matched', 
        store=False
    )

    filtered_product_id = fields.Many2one(
        'product.template',
        string='Product',
        domain="[('is_brand_matched', '=', True)]",
    )

    @api.onchange('filtered_product_id')
    def _compute_is_brand_matched(self):
        """
        Compute if the product matches the selected brand in the invoice.
        """
        for line in self:
            if line.move_id and line.move_id.brand_id:
                brand_id = line.move_id.brand_id.id
                matching_products = self.env['product.template'].search([
                    ('brand_ids', 'in', brand_id)
                ])
                matching_product_ids = matching_products.ids
            else:
                matching_product_ids = []
            all_products = self.env['product.template'].search([])
            for product in all_products:
                product.is_brand_matched = product.id in matching_product_ids