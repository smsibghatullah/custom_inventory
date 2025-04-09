from odoo import models, fields,api

class ResCompany(models.Model):
    _inherit = 'res.company'

    brand_ids = fields.One2many(
        'brand.master',  
        'company_id', 
        string='Brands',
        help='Select the brands associated with this company'
    )

    tag_ids = fields.Many2many(
        'crm.tag',
        'res_company_crm_tag_rel',
        'company_id',
        'tag_id',
        string='Tags',
        help='Select the Tags associated with this user',
    )

    category_ids = fields.One2many(
        'sku.type.master',  
        'company_id', 
        string='Categories',
        help='Select the Categories associated with this company'
    )

    @api.onchange('tag_ids')
    def _onchange_tag_ids(self):
        for tag in self.env['crm.tag'].search([]):
            if self in tag.company_ids and tag not in self.tag_ids:
                tag.company_ids = [(3, self.id)]
            elif self not in tag.company_ids and tag in self.tag_ids:
                tag.company_ids = [(4, self.id)]

class Tag(models.Model):
    _inherit = "crm.tag"

    company_ids = fields.Many2many(
        'res.company',
        'res_company_crm_tag_rel',
        'tag_id',
        'company_id',
        string="Companies using this tag"
    )

    purchase_id = fields.Many2one('purchase.order', string="Purchase")
    invoice_id = fields.Many2one('account.move', string="Invoice")
