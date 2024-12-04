from odoo import models, fields

class ItemMaster(models.Model):
    _name = 'item.master'
    _description = 'Item Master'

    sku_id = fields.Many2one('sku.type.master', string='SKU ID', required=True)
