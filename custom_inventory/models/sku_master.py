from odoo import models, fields,api

class SKUTypeMaster(models.Model):
    _name = 'sku.type.master'
    _description = 'SKU Type Master'

    category_id = fields.Char(string='Category ID', required=True)
    name = fields.Char(string='Name', required=True)
    brand_id = fields.Many2one('brand.master', string='Brand')
    company_id = fields.Many2one('res.company', string="Company")
    user_id = fields.Many2one('res.users', string="Users")



    
