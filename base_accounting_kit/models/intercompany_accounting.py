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
        compute='_compute_source_customer'
    )

    dest_vendor_id = fields.Many2one(
        'res.company', 
        string='Destination Vendor', 
        readonly=True,
        compute='_compute_dest_vendor_id'
    )
    
    brand_ids = fields.Many2many(
        'brand.master',
        string='Brands',
        domain="[('company_ids', '=', dest_company_id)]"
    )
    

    category_ids = fields.Many2many(
        'sku.type.master', 
        string='Categories',
        domain="[('id', 'in', available_sku_category_ids)]" 
    )

    available_sku_category_ids = fields.Many2many(
        'sku.type.master',
        compute="_compute_available_categories",
    )

    tag_ids = fields.Many2many(
        'crm.tag',
        string='Tags',
        domain="[('company_ids', '=', dest_company_id)]"
    )

    destination_gl_account_id = fields.Many2one(
        'account.account', 
        string='Destination GL Account', 
        required=True,
        domain="[('company_id', '=', dest_company_id), ('deprecated', '=', False)]"
    )

    @api.onchange('dest_company_id')
    def _onchange_destination_company(self):
        self.brand_ids = False
        self.category_ids = False  
        self.tag_ids = False
        
    @api.depends("brand_ids")
    def _compute_available_categories(self):
        for record in self:
            selected_brand_ids = record.brand_ids.ids
            
            if not selected_brand_ids:
                record.available_sku_category_ids = False
                continue

            available_categories = self.env['sku.type.master'].search([
                ('brand_id', 'in', selected_brand_ids) 
            ])
            
            record.available_sku_category_ids = available_categories
    
    @api.depends('source_company_id')
    def _compute_dest_vendor_id(self):
        self.dest_vendor_id = self.source_company_id.id
    
    @api.depends('dest_company_id')
    def _compute_source_customer(self):
        self.source_customer_id = self.dest_company_id.id


class PurchaseBillParameter(models.Model):
    _name = 'purchase.bill.parameter'
    _description = 'Purchase Bill Parameter'

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

    source_vendor_id = fields.Many2one(
        'res.company', 
        string='Source Vendor', 
        readonly=True,
        compute='_compute_source_vendor',
    )

    dest_customer_id = fields.Many2one(
        'res.company', 
        string='Destination Customer', 
        readonly=True,
        compute='_compute_dest_customer'
    )
    
    brand_ids = fields.Many2many(
        'brand.master',
        string='Brands',
        domain="[('company_ids', '=', dest_company_id)]"
    )
    
    category_ids = fields.Many2many(
        'sku.type.master', 
        string='Categories',
        domain="[('id', 'in', available_sku_category_ids)]" 
    )

    available_sku_category_ids = fields.Many2many(
        'sku.type.master',
        compute="_compute_available_categories",
    )

    tag_ids = fields.Many2many(
        'crm.tag',
        string='Tags',
        domain="[('company_ids', '=', dest_company_id)]"
    )

    destination_gl_account_id = fields.Many2one(
        'account.account', 
        string='Destination GL Account',
        required=True,
        domain="[('company_id', '=', dest_company_id), ('deprecated', '=', False)]"
    )

    @api.onchange('dest_company_id')
    def _onchange_destination_company(self):
        self.brand_ids = False
        self.category_ids = False  
        self.tag_ids = False

    @api.depends('dest_company_id')
    def _compute_source_vendor(self):
        self.source_vendor_id = self.dest_company_id.id
    
    @api.depends('source_company_id')
    def _compute_dest_customer(self):
        self.dest_customer_id = self.source_company_id.id
        
    @api.depends("brand_ids")
    def _compute_available_categories(self):
        for record in self:
            selected_brand_ids = record.brand_ids.ids
            
            if not selected_brand_ids:
                record.available_sku_category_ids = False
                continue

            available_categories = self.env['sku.type.master'].search([
                ('brand_id', 'in', selected_brand_ids) 
            ])
            
            record.available_sku_category_ids = available_categories

