from odoo import models, fields

class SKUTypeMaster(models.Model):
    _name = 'sku.type.master'
    _description = 'SKU Type Master'

    sku_id = fields.Char(string='SKU ID', required=True)
    name = fields.Char(string='Name', required=True)
    brand_id = fields.Many2one('brand.master', string='Brand')


