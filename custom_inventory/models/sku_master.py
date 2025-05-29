from odoo import models, fields,api

class SKUTypeMaster(models.Model):
    _name = 'sku.type.master'
    _description = 'SKU Type Master'

    category_id = fields.Char(string='Category ID', required=True)
    name = fields.Char(string='Name', required=True)
    brand_id = fields.Many2one('brand.master', string='Brand')
    company_ids = fields.Many2many(
        'res.company',
        'sku_category_company_rel',
        'category_id',
        'company_id',
        string="Companies using this tag"
    )



    
