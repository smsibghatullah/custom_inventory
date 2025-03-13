from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    brand_ids = fields.One2many(
        'brand.master',  
        'company_id', 
        string='Brands',
        help='Select the brands associated with this company'
    )