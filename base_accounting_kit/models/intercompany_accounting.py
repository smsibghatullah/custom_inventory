from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)
from markupsafe import Markup

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
        domain=lambda self: [('id', 'in', self.env['intercompany.parameter'].search([("source_company_id", "=", self.env.company.id)]).mapped('source_company_id').ids)],
    )

    destination_company_id = fields.Many2one(
        'res.company',
        string='Destination Company',
    )

    available_destination_companies = fields.Many2many(
        'res.company',
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
    auto_created_doc = fields.Boolean(
        store=True,
        default=False,
    )

    @api.depends('destination_company_id', 'brand_id')
    def _compute_available_boms_by_company(self):
        for move in self: 
            move.available_bom_ids = False
            domain = []

            domain.append(('company_id', '=', self.env.company.id))
            
            if move.brand_id:
                domain.append(('brand_id', '=', move.brand_id.id))

            if domain:
                boms = self.env['bom.products'].search(domain)
                move.available_bom_ids = [(6, 0, boms.ids)]

    @api.depends('destination_company_id', 'intercompany')
    def _compute_available_brands(self):
        default_brands = self.env['brand.master'].search([
                ('company_ids', 'in', self.env.company.id)
            ])        
        if default_brands:
                self.available_brands_ids = [(6, 0, default_brands.ids)]

    @api.onchange('intercompany')
    def _onchange_set_customer_partner_id(self):
        if not self.intercompany:
            self.source_company_id = False
        
        elif self.intercompany:
            self.source_company_id = self.env.company.id
            self.set_destination_company()

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.intercompany and self.partner_id and self.source_company_id:
            self.set_destination_company()
        elif not self.intercompany:
            self.destination_company_id = False

    def set_destination_company(self):
        destination_param = False
        intercompany_param = self.env['intercompany.parameter'].search(
                [('source_company_id', '=', self.source_company_id.id)],
                limit=1
            )
        if not intercompany_param:
            self.destination_company_id = False
            return

        if intercompany_param and self.move_type == "out_invoice":
            destination_param = intercompany_param.intercompany_invoice_destination_company_ids.filtered(
                lambda r: r.source_customer_id.id == self.partner_id.id
            )
        elif intercompany_param and self.move_type == "in_invoice":
            destination_param = intercompany_param.intercompany_bill_destination_company_ids.filtered(
                lambda r: r.source_customer_id.id == self.partner_id.id
            )
            
        if self.partner_id and destination_param:
            _logger.info(f"==== {destination_param}")
            self.destination_company_id = destination_param[0].destination_company_id.id

        else:
            self.destination_company_id = False


    @api.depends('intercompany', 'source_company_id')
    def _compute_allowed_partner_ids(self):
        for record in self:
            if record.intercompany and record.source_company_id:
                params = self.env['intercompany.parameter'].search([
                    ('source_company_id', '=', self.source_company_id.id)
                ])
                if params and self.move_type == "out_invoice":
                    record.allowed_partner_ids = params.mapped('intercompany_invoice_destination_company_ids.source_customer_id').ids
                elif params and self.move_type == "in_invoice":
                    record.allowed_partner_ids = params.mapped('intercompany_bill_destination_company_ids.source_customer_id').ids
                else:
                    record.allowed_partner_ids = False
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
                    ic_param = self.env['intercompany.parameter'].sudo().search([
                        ('source_company_id', '=', move.source_company_id.id),
                    ], limit=1)

                    if ic_param:
                        source_param = ic_param.intercompany_invoice_destination_company_ids.filtered(
                            lambda r: r.source_customer_id.id == move.partner_id.id
                        )

                        if source_param:
                            gl_account_id = source_param.destination_bill_gl_account_id.id
                            
                            # partner_id_for_bill = move.partner_id.id
                            
                            # if not gl_account_id or not partner_id_for_bill:
                            #     raise ValidationError("Intercompany parameters are incomplete (missing GL Account or Customer mapping).")
                            
                            # purchase_journal = self.env['account.journal'].sudo().search([
                            #     ('type', '=', 'purchase'),
                            #     ('company_id', '=', move.destination_company_id.id),
                            #     ('code', '=', 'BILL'),
                            # ], limit=1)
                            # self.env['account.journal'].sudo().search([
                            #     ('type', '=', 'purchase'),
                            #     ('company_id', '=', gl_account_id), # Ab move.destination_company_id ke bajaye account_company_id use ho raha hy
                            #     # Note: 'BILL' code ab bhi generic use ho raha hy, ya aap isay bhi config se utha saktay hain agar zaroorat ho
                            #     ('code', '=', 'BILL'), 
                            # ], limit=1)

                            # if not purchase_journal:
                            #     raise ValidationError(f"Purchase journal 'BILL' not found for company {move.destination_company_id.name}")
                            
                            line_vals = []
                            for line in move.invoice_line_ids:
                                line_vals.append((0, 0, {
                                    'product_id': line.product_id.id,
                                    'quantity': line.quantity,
                                    'price_unit': line.price_unit,
                                    'name': line.name,
                                    'account_id': gl_account_id,
                                    'display_type': line.display_type,
                                }))

                            first_brand_id = move.get_first_id(source_param.brand_ids)
                            first_category_id = move.get_first_id(source_param.category_ids)
                            first_tag_id = move.get_first_id(source_param.tag_ids)

                            dest_move_vals = {
                                'invoice_date': self.invoice_date,
                                # 'journal_id': purchase_journal.id,
                                'partner_id': source_param.destination_vendor_id.id,
                                'company_id': self.destination_company_id.id,
                                'source_company_id': self.source_company_id.id,
                                'destination_company_id': self.destination_company_id.id,
                                'customer_description': self.customer_description,
                                'reference': self.reference,
                                'payment_reference': self.payment_reference,
                                'intercompany': True,
                                'move_type': "in_invoice",
                                'auto_created_doc': True,
                                'brand_id': first_brand_id,
                                'bom_id': self.bom_id.id if self.bom_id else False,                                
                                'category_ids': [(6, 0, [first_category_id])] if first_category_id else False,
                                'tag_ids': [(6, 0, [first_tag_id])] if first_tag_id else False,
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
                            result.reference = self.reference
                            result.action_post()
                            # result.sudo().action_post()

                            message_body = f"""
                                <p>Bill Created.</p>
                                <ul>
                                    <li><strong>Source company:</strong> <a href="#" data-oe-id="{self.source_company_id.id}" data-oe-model="account.move">{self.source_company_id.name}</a></li>
                                    <li><strong>Destination Company:</strong> {move.destination_company_id.name}</li>
                                    <li><strong>Bill Entry :</strong> <a href="#" data-oe-id="{result.id}" data-oe-model="account.move">{result.name}</a></li>
                                </ul>
                            """
                            self.message_post(
                                body=Markup(message_body),
                                subject="Purchase Bill Created",
                                message_type='comment',
                                subtype_xmlid='mail.mt_note'
                            )

                elif move.move_type == "in_invoice":
                    """
                    Creating auto invoice when Bill is created in source company.
                    1. fetch details from 'sales.invoice.parameter' and fetch account from destination company
                    2. create invoice in the destination company
                    """
                    _logger.info("CREATING DESTINATION INVOICE")

                    ic_param = self.env['intercompany.parameter'].sudo().search([
                        ('source_company_id', '=', move.source_company_id.id),
                    ], limit=1)

                    if ic_param:
                        source_param = ic_param.intercompany_bill_destination_company_ids.filtered(
                            lambda r: r.source_customer_id.id == move.partner_id.id
                        )
                    
                        if source_param:
                            invoice_vals = move._prepare_intercompany_invoice_vals(move.destination_company_id, source_param)
                            result = self.env['account.move'].sudo().create(invoice_vals)
                            result.action_post()

                            message_body = f"""
                                <p>Invoice Created.</p>
                                <ul>
                                    <li><strong>Source company:</strong> <a href="#" data-oe-id="{self.source_company_id.id}" data-oe-model="account.move">{self.source_company_id.name}</a></li>
                                    <li><strong>Destination Company:</strong> {move.destination_company_id.name}</li>
                                    <li><strong>Invoice Entry :</strong> <a href="#" data-oe-id="{result.id}" data-oe-model="account.move">{result.name}</a></li>
                                </ul>
                            """
                            self.message_post(
                                body=Markup(message_body),
                                subject="Sales Invoice Created",
                                message_type='comment',
                                subtype_xmlid='mail.mt_note'
                            )
                    else:
                         _logger.info("Skipping sales invoice creation: Parameters not found for reverse flow.")
        return super(AccountMove, move).action_post()

    def get_first_id(self, recordset):
        return recordset[0].id if recordset else False
    
    def _prepare_intercompany_invoice_vals(self, destination_company, source_param):
        """Prepares values for the Sales Invoice in the Source Company context."""
        
        gl_account_id = source_param.destination_invoice_gl_account_id.id
        _logger.info(f"sale.invoice.oaram dest account invoice {gl_account_id}")
        
        first_brand_id = self.get_first_id(source_param.brand_ids)
        first_category_id = self.get_first_id(source_param.category_ids)
        first_tag_id = self.get_first_id(source_param.tag_ids)

        return {
            'move_type': 'out_invoice',
            'partner_id': source_param.destination_vendor_id.id,
            'company_id': destination_company.id,
            'invoice_date': self.invoice_date,
            'reference': self.reference,
            'payment_reference': self.payment_reference,
            'intercompany': True, 
            'source_company_id': self.source_company_id.id,
            'destination_company_id': self.destination_company_id.id,
            'customer_description': self.customer_description,
            'brand_id': first_brand_id,
            'auto_created_doc': True,
            'bom_id': self.bom_id.id if self.bom_id else False,                                
            'category_ids': [(6, 0, [first_category_id])] if first_category_id else False,
            'tag_ids': [(6, 0, [first_tag_id])] if first_tag_id else False,
            
            'invoice_line_ids': [(0, 0, {
                'product_id': line.product_id.id,
                'quantity': line.quantity,
                'price_unit': line.price_unit,
                'name': line.name,
                'account_id': gl_account_id, 
            }) for line in self.invoice_line_ids],
        }