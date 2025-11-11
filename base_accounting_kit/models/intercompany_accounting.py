from odoo import models, fields, api, _

class SalesInvoiceParameter(models.Model):
    _name = 'sales.invoice.parameter'
    _description = 'Sales Invoice Parameter'

    source_company_id = fields.Many2one(
        'res.company', 
        string='Source Company', 
        required=True, 
    )

    dest_company_id = fields.Many2one(
        'res.company', 
        string='Destination Company', 
        required=True,
        domain="[('id', '!=', source_company_id)]"
    )

    source_customer_id = fields.Many2one(
        'res.company', 
        string='Source Customer', 
        readonly=True,
    )

    dest_vendor_id = fields.Many2one(
        'res.company', 
        string='Destination Vendor', 
        readonly=True,
    )
    
    brand_ids = fields.Many2many(
        'brand.master',
        string='Brands'
    )
    
    category_ids = fields.Many2many(
        'sku.type.master', 
        string='Categories',
    )

    tag_ids = fields.Many2many(
        'crm.tag',
        string='Tags'
    )

    destination_gl_account_id = fields.Many2one(
        'account.account', 
        string='Destination GL Account', 
        required=True,
        domain="[('company_id', '=', dest_company_id), ('deprecated', '=', False)]"
    )

    @api.onchange('dest_company_id')
    def _onchange_destination_company(self):
        self.source_customer_id = self.dest_company_id.id
        brand_domain = []
        category_domain = []
        tag_domain = []

        if self.dest_company_id:
            brand_domain = [('company_ids', 'in', self.dest_company_id.id)]
            tag_domain = [('company_ids', 'in', self.dest_company_id.id)]
            
            category_domain = [('company_id', '=', self.dest_company_id.id)]
        
        return {
            'domain': {
                'brand_ids': brand_domain,
                'category_ids': category_domain,
                'tag_ids': tag_domain,
            }
        }
    
    @api.onchange('source_company_id')
    def _onchange_source_company_set_vendor(self):
        self.dest_vendor_id = self.source_company_id.id
