from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    brand_ids = fields.One2many(
        'brand.master',  
        'company_id', 
        string='Brands',
        help='Select the brands associated with this company'
    )

    tag_ids = fields.One2many(
        'crm.tag',  
        'company_id', 
        string='Tags',
        help='Select the Tags associated with this company'
    )

    category_ids = fields.One2many(
        'sku.type.master',  
        'company_id', 
        string='Categories',
        help='Select the Categories associated with this company'
    )

class Tag(models.Model):
    _inherit = "crm.tag"

    company_id = fields.Many2one('res.company', string="Company")
    purchase_id = fields.Many2one('purchase.order', string="Purchase")
    invoice_id = fields.Many2one('account.move', string="Invoice")

