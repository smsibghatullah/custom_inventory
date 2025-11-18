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
        'res.partner', 
        string='Source Customer', 
        required=True,
    )

    dest_vendor_id = fields.Many2one(
        'res.partner', 
        string='Destination Vendor', 
        required=True,
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
        domain=lambda self: [('id', 'in', self.env['sales.invoice.parameter'].search([("source_company_id", "=", self.env.company.id)]).mapped('source_company_id').ids)],
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
    allowed_partner_ids = fields.Many2many('res.partner', compute='_compute_allowed_partner_ids')


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
            self.source_company_id = False
            return {'domain': {'partner_id': []}}
        
        elif self.intercompany:
            self.source_company_id = self.env.company.id
            _logger.info(f"Source COmpany SET==== {self.source_company_id}")
            params = self.env['sales.invoice.parameter'].search([
                ('source_company_id', '=', self.source_company_id.id)
            ])
            allowed_partners = params.mapped('source_customer_id').ids
            _logger.info(f"Source COmpany SET==== {allowed_partners}")

            return {
                'domain': {
                    'partner_id': [('id', 'in', allowed_partners)]
                }
            }

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.intercompany:
            sale_inv_param = self.env['sales.invoice.parameter'].search(
                [('source_company_id', '=', self.source_company_id.id), ('source_customer_id', '=', self.partner_id.id)], 
            limit=1)
            
            self.destination_company_id = sale_inv_param.dest_company_id 

    @api.depends('intercompany', 'source_company_id')
    def _compute_allowed_partner_ids(self):
        for record in self:
            if record.intercompany and record.source_company_id:
                params = self.env['sales.invoice.parameter'].search([('source_company_id', '=', record.source_company_id.id)])
                record.allowed_partner_ids = params.mapped('source_customer_id')
            else:
                partner_domain = [
                    '|',
                    ('company_id', '=', self.env.company.id),
                    ('company_id', '=', False),
                ]
                partners = self.env['res.partner'].sudo().search(partner_domain)
                record.allowed_partner_ids = partners

    def action_post(self):
        for move in self:
            if not move.partner_id and move.intercompany and move.source_company_id and move.source_company_id.partner_id:
                move.partner_id = move.source_company_id.partner_id.id

            if not move.intercompany:
                return super(AccountMove, move).action_post()
            else:
                if not move.source_company_id or not move.destination_company_id:
                     raise ValidationError("Source and Destination companies must be set.")
                if move.move_type in ['out_invoice', 'out_refund']:
                    """
                    Creating auto purchase bill when Invoice is created in source company.
                    1. fetch details from 'purhcase.bill.parameter' and fetch account from destination company
                    2. create bill in the destination company
                    """
                    bill_params = self.env['purchase.bill.parameter'].sudo().search([
                        ('source_company_id', '=', move.source_company_id.id),
                        ('dest_company_id', '=', move.destination_company_id.id)
                    ], limit=1)

                    if bill_params:
                        gl_account_id = bill_params.destination_gl_account_id.id
                        purchase_journal = self.env['account.journal'].sudo().search([
                            ('type', '=', 'purchase'),
                            ('company_id', '=', move.destination_company_id.id),
                            ('code', '=', 'BILL'),
                        ], limit=1)
                        if not purchase_journal:
                            raise ValidationError(f"Purchase journal 'BILL' not found for company {move.destination_company_id.name}")
                        
                        dest_move_vals = {
                            'invoice_date': self.invoice_date,
                            'journal_id': purchase_journal.id,
                            'company_id': self.destination_company_id.id,
                            'source_company_id': self.source_company_id.id,
                            'destination_company_id': self.destination_company_id.id,
                            'customer_description': self.customer_description,
                            'reference': self.reference,
                            'intercompany': True,
                            'move_type': "in_invoice",
                            'brand_id': self.brand_id.id if self.brand_id else False,
                            'bom_id': self.bom_id.id if self.bom_id else False,
                            'category_ids': [(6, 0, move.category_ids.ids)] if move.category_ids else False,
                            'tag_ids': [(6, 0, move.tag_ids.ids)] if move.tag_ids else False,
                            'line_ids': [(0, 0, {
                                'product_id': line.product_id.id,
                                'quantity': line.quantity,
                                'price_unit': line.price_unit,
                                'name': line.name,
                                'account_id': gl_account_id,
                            }) for line in move.invoice_line_ids]
                        }
                        result = self.env['account.move'].sudo().create(dest_move_vals)
                        result.invoice_date = self.invoice_date
                        result.journal_id = purchase_journal.id
                        result.reference = self.reference

                elif move.move_type == "in_invoice":
                    """
                    Creating auto invoice when Bill is created in source company.
                    1. fetch details from 'sales.invoice.parameter' and fetch account from destination company
                    2. create invoice in the destination company
                    """
                    _logger.info("CREATING DESTINATION INVOICE")
                    sales_invoice_params = self.env['sales.invoice.parameter'].sudo().search([
                        ('source_company_id', '=', move.source_company_id.id),
                        ('dest_company_id', '=', move.destination_company_id.id), 
                    ], limit=1)
                    
                    if sales_invoice_params:
                        invoice_vals = move._prepare_intercompany_invoice_vals(move.destination_company_id, sales_invoice_params)
                        self.env['account.move'].sudo().create(invoice_vals)
                    else:
                         _logger.info("Skipping sales invoice creation: Parameters not found for reverse flow.")
        return super(AccountMove, move).action_post()

    def _prepare_intercompany_invoice_vals(self, destination_company, sales_invoice_param):
        """Prepares values for the Sales Invoice in the Source Company context."""
        
        gl_account_id = sales_invoice_param.destination_gl_account_id.id
        _logger.info(f"sale.invoice.oaram dest account invoice {gl_account_id}")
        
        sales_journal = self.env['account.journal'].sudo().search([
            ('type', '=', 'sale'),
            ('company_id', '=', destination_company.id),
            ('code', '=', 'INV'),
        ], limit=1)
        _logger.info(f"sale.invoice.oaram journal {sales_journal}")
        if not sales_journal:
            raise ValidationError(f"Invoice journal 'INV' not found for company {destination_company.name}")
        

        return {
            'move_type': 'out_invoice',
            'partner_id': destination_company.partner_id.id,
            'journal_id': sales_journal.id,
            'company_id': destination_company.id,
            'invoice_date': self.invoice_date,
            'reference': self.reference,
            'intercompany': True, 
            'source_company_id': self.source_company_id.id,
            'destination_company_id': self.destination_company_id.id,
            'customer_description': self.customer_description,
            'brand_id': self.brand_id.id if self.brand_id else False,
            'bom_id': self.bom_id.id if self.bom_id else False,
            'category_ids': [(6, 0, self.category_ids.ids)] if self.category_ids else False,
            'tag_ids': [(6, 0, self.tag_ids.ids)] if self.tag_ids else False,
            
            'invoice_line_ids': [(0, 0, {
                'product_id': line.product_id.id,
                'quantity': line.quantity,
                'price_unit': line.price_unit,
                'name': line.name,
                'account_id': gl_account_id, 
            }) for line in self.invoice_line_ids],
        }