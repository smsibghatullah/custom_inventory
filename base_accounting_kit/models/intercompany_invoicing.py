from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from markupsafe import Markup


import logging
_logger = logging.getLogger(__name__)

class IntercompanyParameter(models.Model):
    _name = 'intercompany.parameter'
    _description = 'Intercompany Parameter'

    source_company_id = fields.Many2one(
        'res.company', 
        string='Source Company', 
        required=True, 
    )

    destination_vendor_id = fields.Many2one(
        'res.partner', 
        string='Destination Vendor', 
    )

    intercompany_invoice_destination_company_ids = fields.One2many(
        'intercompany.destination.parameter', 
        'intercompany_parameter_id',
        domain=[('parameter_type', '=', 'invoice')]
    )

    intercompany_bill_destination_company_ids = fields.One2many(
        'intercompany.destination.parameter', 
        'intercompany_parameter_id',
        domain=[('parameter_type', '=', 'bill')]
    )

    #Deprecated: should be removed
    intercompany_destination_company_ids = fields.One2many(
        'intercompany.destination.parameter', 
        'intercompany_parameter_id',
        string='Intercompany Destination Companies'
    )


class IntercompanyDestinationParameter(models.Model):
    _name = 'intercompany.destination.parameter'
    _description = 'Intercompany Destination Parameter'

    intercompany_parameter_id = fields.Many2one('intercompany.parameter', string='Intercompany Source Parameter', required=True, ondelete='cascade')

    parameter_type = fields.Selection([
        ('invoice', 'Sales Invoice'),
        ('bill', 'Purchase Bill'),
    ], string='Parameter Type', required=True, default='invoice')

    intercompany_source_company_id = fields.Many2one(
        'res.company',
        string='Source Company',
        related='intercompany_parameter_id.source_company_id',
        store=False,
        readonly=True
    )

    destination_company_id = fields.Many2one(
        'res.company', 
        string='Destination Company', 
        required=True,
    )

    destination_vendor_id = fields.Many2one(
        'res.partner', 
        string='Destination Vendor', 
        required=True,
    )

    source_customer_id = fields.Many2one(
        'res.partner', 
        string='Source Customer', 
        required=True,
    )
    
    brand_ids = fields.Many2many(
        'brand.master',
        string='Brands',
        domain="[('company_ids', '=', destination_company_id)]"
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
        domain="[('company_ids', '=', destination_company_id)]"
    )

    destination_invoice_gl_account_id = fields.Many2one(
        'account.account', 
        string='Destination Invoice Account', 
        required=True,
        domain="[('company_id', '=', destination_company_id), ('deprecated', '=', False)]"
    )

    destination_bill_gl_account_id = fields.Many2one(
        'account.account', 
        string='Destination Bill Account', 
        required=True,
        domain="[('company_id', '=', destination_company_id), ('deprecated', '=', False)]"
    )

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