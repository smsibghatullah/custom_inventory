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


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    brand_ids = fields.Many2many(
        'brand.master',
        'product_brand_rel',
        'product_id',
        'brand_id',
        string='Brands',
    )
    is_brand_matched = fields.Boolean(string='Is Brand Matched', default=False)

    @api.onchange('brand_ids')
    def _onchange_brand_ids(self):
        """
        This method is triggered when brand_ids is changed in product.template.
        It updates the is_brand_matched field in the related product.product records
        and also sets the brand_ids for each product.
        """
        for template in self:
            if template.brand_ids:
                template.is_brand_matched = True
            else:
                template.is_brand_matched = False

            for product in template.product_variant_ids:
                product.is_brand_matched = template.is_brand_matched
                product.brand_ids = template.brand_ids
                print(product.name,"pppppppppppppppppppppppppppppppp===============>>>>>>>>>>")  


    @api.model
    def create(self, vals):
        """
        Override the create method to ensure that is_brand_matched and brand_ids are set correctly for new products.
        """
        template = super(ProductTemplate, self).create(vals)
        template._onchange_brand_ids() 
        return template

    @api.model
    def write(self, vals):
        """
        Override the write method to ensure that is_brand_matched and brand_ids are set correctly for updated products.
        """
        res = super(ProductTemplate, self).write(vals)
        if 'brand_ids' in vals:
            self._onchange_brand_ids()
        return res


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


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    brand_id = fields.Many2one(
        'brand.master', 
        string='Brand',
        help='Select the brand associated with this sale order'
    )

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

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
        Compute if the product matches the selected brand in the sale order.
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