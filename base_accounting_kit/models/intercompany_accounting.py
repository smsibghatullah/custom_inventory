from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)

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


class AccountMove(models.Model):
    _inherit = 'account.move'

    intercompany = fields.Boolean(
        string='Intercompany',
        default=False,
        help='Check this box to enable intercompany invoicing'
    )

    source_company_id = fields.Many2one(
        'res.company',
        string='Source Company',
        domain=lambda self: [('id', 'in', self.env['sales.invoice.parameter'].search([]).mapped('source_company_id').ids)],
    )

    destination_company_id = fields.Many2one(
        'res.company',
        string='Destination Company',
    )

    available_destination_companies = fields.Many2many(
        'res.company',
        compute='_compute_available_destination_companies',
        store=False,
    )

    available_brands_ids = fields.Many2many(
        'brand.master',
        compute='_compute_available_brands',
        store=False,
    )

    available_bom_ids = fields.Many2many(
        'bom.products', 
        string='Available BOMs (Internal)', 
        compute='_compute_available_boms_by_company',
        store=False,
    )

    @api.depends('destination_company_id', 'brand_id')
    def _compute_available_boms_by_company(self):
        for move in self: 
            move.available_bom_ids = False
            domain = []

            if move.destination_company_id:
                domain.append(('company_id', '=', move.destination_company_id.id))
            
            if move.brand_id:
                domain.append(('brand_id', '=', move.brand_id.id))

            if domain:
                boms = self.env['bom.products'].with_company(move.destination_company_id.id).sudo().search(domain)
                move.available_bom_ids = [(6, 0, boms.ids)]
        
        

    @api.onchange('source_company_id')
    def _onchange_filter_bom_products_by_company(self):
         if self.bom_id and self.bom_id not in self.available_bom_ids:
             self.bom_id = False
         return {'domain': {}} 

    @api.depends('destination_company_id', 'intercompany')
    def _compute_available_brands(self):
        
        self.available_brands_ids = False
        
        if self.intercompany and self.destination_company_id:
            sales_invoice_params = self.env['sales.invoice.parameter'].search([('dest_company_id', '=', self.destination_company_id.id), ('source_company_id', '=', self.source_company_id.id)])
            self.available_brands_ids = [(6, 0, sales_invoice_params.brand_ids.ids)]
        
        else:
            default_brands = self.env['brand.master'].search([
                    ('company_ids', 'in', self.env.company.id)
                ])        
            if default_brands:
                    self.available_brands_ids = [(6, 0, default_brands.ids)]


    @api.depends('destination_company_id', 'intercompany', 'source_company_id')
    def _compute_available_tags(self):
        
        self.available_tag_ids = False
        
        if self.intercompany and self.destination_company_id:
            sales_invoice_params = self.env['sales.invoice.parameter'].search([
                ('dest_company_id', '=', self.destination_company_id.id), 
                ('source_company_id', '=', self.source_company_id.id)
            ], limit=1)
            
            if sales_invoice_params and sales_invoice_params.tag_ids:
                self.available_tag_ids = [(6, 0, sales_invoice_params.tag_ids.ids)]

        else:
            self.available_tag_ids = self.env.user.tag_ids
            
        if self.tag_ids and not all(tag in self.available_tag_ids for tag in self.tag_ids):
            self.tag_ids = False             

    @api.depends('source_company_id')
    def _compute_available_destination_companies(self):
        for move in self:
            move.available_destination_companies = False
            
            if move.source_company_id:
                dest_company_ids = self.env['sales.invoice.parameter'].search([
                    ('source_company_id', '=', move.source_company_id.id)
                ]).mapped('dest_company_id').ids
                
                move.available_destination_companies = self.env['res.company'].browse(dest_company_ids)

    @api.onchange('destination_company_id')
    def _onchange_clear_brand_and_category(self):
        if self.brand_id:
            self.brand_id = False
            
        if self.category_ids:
            self.category_ids = False 

    @api.onchange('intercompany', 'destination_company_id')
    def _onchange_set_customer_partner_id(self):
        if not self.intercompany:
            self.partner_id = False
        
        elif self.intercompany:
            if self.destination_company_id:
                default_partner = self.destination_company_id.primary_partner
                
                if default_partner:
                    self.partner_id = default_partner.id
                else:
                    self.partner_id = False
            else:
                self.partner_id = False

    def action_post(self):
        for move in self:
            if not move.intercompany:
                return super(AccountMove, move).action_post()
            else:
                if not move.source_company_id or not move.destination_company_id:
                     raise ValidationError("Source and Destination companies must be set.")
                if move.move_type not in ['out_invoice', 'out_refund']:
                    return super(AccountMove, move).action_post()

                bill_params = self.env['purchase.bill.parameter'].sudo().search([
                    ('source_company_id', '=', move.source_company_id.id),
                    ('dest_company_id', '=', move.destination_company_id.id)
                ], limit=1)

                if bill_params:
                    dest_move_vals = {
                        'invoice_date': self.invoice_date,
                        'journal_id': 2,
                        'company_id': self.destination_company_id.id,
                        'ref': self.reference,
                        'move_type': "in_invoice",
                        'invoice_line_ids': [(0, 0, {
                            'product_id': line.product_id.id,
                            'quantity': line.quantity,
                            'price_unit': line.price_unit,
                            'name': line.name,
                            'account_id': 30, 
                        }) for line in self.invoice_line_ids]
                    }
                    _logger.info(f"purchase BILL data {dest_move_vals}")
                    result = self.env['account.move'].sudo().create(dest_move_vals)
                    result.invoice_date = self.invoice_date
                    result.journal_id = 2
                    result.reference = self.reference
                    _logger.info(f"purchase BILL {result}")

                source_move_vals = {
                    'date': self.invoice_date,
                    'journal_id': 10,
                    'company_id': self.source_company_id.id,
                    'ref': self.ref,
                    'move_type': "out_invoice",
                    'invoice_line_ids': [(0, 0, {
                        'product_id': line.product_id.id,
                        'quantity': line.quantity,
                        'price_unit': line.price_unit,
                        'name': line.name,
                        'account_id': 104, 
                    }) for line in self.invoice_line_ids]
                }
                _logger.info(f"source mov vale {source_move_vals}")
                result = self.env['account.move'].sudo().create(source_move_vals)
                _logger.info(f"source mov vale done!! {result}")
                
        return super(AccountMove, move).action_post()

    def _prepare_intercompany_bill_vals(self, destination_company, partner, bill_parameter):
        gl_account_id = bill_parameter.destination_gl_account_id.id
        if not gl_account_id:
             raise ValidationError(f"Missing Destination GL Account on Purchase Bill Parameter record ID: {bill_parameter.id}")
        return {
            'move_type': 'in_invoice', 
            'partner_id': partner.id, 
            'company_id': destination_company.id,
            'source_company_id': self.source_company_id.id,
            'destination_company_id': self.destination_company_id.id,
            'intercompany': True, 
            'brand_id': self.brand_id.id if self.brand_id else False,
            'customer_description': self.customer_description, 
            'category_ids': [(6, 0, self.category_ids.ids)] if self.category_ids else False,
            'tag_ids': [(6, 0, self.tag_ids.ids)] if self.tag_ids else False,
            'invoice_date': self.invoice_date,
            'currency_id': self.currency_id.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': line.product_id.id,
                'quantity': line.quantity,
                'price_unit': line.price_unit,
                'name': line.name,
                'account_id': gl_account_id, 
            }) for line in self.invoice_line_ids],
        }