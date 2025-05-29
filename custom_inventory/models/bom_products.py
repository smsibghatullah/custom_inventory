from odoo import models, fields, api

class BomProducts(models.Model):
    _name = 'bom.products'
    _description = 'Bill of Materials Products'

    name = fields.Char(string='BOM Name', required=True)
    line_product_ids = fields.One2many('bom.product.line', 'bom_id', string='Products')
    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True, index=True,
        default=lambda self: self.env.company)
    brand_id = fields.Many2one(
        'brand.master', 
        string='Brand *',
        required=True,
        domain="[('company_ids', 'in', company_id)]",
        help='Select the brand associated with this sale order'
    )

    category_ids = fields.Many2many(
        'sku.type.master',
        'bom_category_rel',
        'product_id',
        'category_id',
        string='Categories *',
         required=True,
        help='Select the Categories associated with the selected brand'
    )

    available_sku_category_ids = fields.Many2many(
        'sku.type.master',
        compute="_compute_available_categories",
    )
   
    @api.depends("category_ids")
    def _compute_available_categories(self):
        for record in self:
            record.available_sku_category_ids = self.env.user.sku_category_ids

class BomProductLine(models.Model):
    _name = 'bom.product.line'
    _description = 'BOM Product Line'

    bom_id = fields.Many2one('bom.products', string='BOM')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_uom_qty = fields.Float(string='Quantity', required=True)
    product_uom = fields.Many2one('uom.uom', string='UOM')
    category_ids = fields.Many2many(
        'sku.type.master',
        'bom_line_category_rel_we',
        'product_id',
        'category_id',
        string=' ',
        compute='_compute_product_sku_id',
        required=True,
        store=True,
        help='Select the Categories associated with the selected brand'
    )

    @api.depends('bom_id.category_ids')
    def _compute_product_sku_id(self):
        for line in self:
            print(f"Order ID: {line.bom_id.id}, BOM ID: {line.bom_id}")
            print(f"Before Compute: {line.category_ids}")

            if line.bom_id and line.bom_id.category_ids:
                    line.category_ids = line.bom_id.category_ids.ids
            else:
                category_ids = self.env['sku.type.master'].search([]) 
                line.category_ids = category_ids

            print(f"After Compute: {line.category_ids}")


    @api.onchange('category_ids')
    def _onchange_category_ids(self):
        for line in self:
            return {'domain': {'product_id': [('category_ids', 'in', line.category_ids.ids)]}}

    @api.onchange('product_id')
    def _compute_product_template_id(self):
        print('kkkkkkkkkkkkkkkkkkkkk')
        for line in self:
            if line.bom_id and line.bom_id.category_ids:
                    line.category_ids = line.bom_id.category_ids.ids
            else:
                category_ids = self.env['sku.type.master'].search([]) 
                line.category_ids = category_ids

            print("yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy")
