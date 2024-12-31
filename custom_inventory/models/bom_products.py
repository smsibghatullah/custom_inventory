from odoo import models, fields, api

class BomProducts(models.Model):
    _name = 'bom.products'
    _description = 'Bill of Materials Products'

    name = fields.Char(string='BOM Name', required=True)
    line_product_ids = fields.One2many('bom.product.line', 'bom_id', string='Products')

class BomProductLine(models.Model):
    _name = 'bom.product.line'
    _description = 'BOM Product Line'

    bom_id = fields.Many2one('bom.products', string='BOM')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_uom_qty = fields.Float(string='Quantity', required=True)
    product_uom = fields.Many2one('uom.uom', string='UOM')
