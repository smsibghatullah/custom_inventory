from odoo import models, fields, api, _
from odoo.exceptions import UserError
from markupsafe import Markup


import logging
_logger = logging.getLogger(__name__)

class IntercompanyTradingParameter(models.Model):
    _name = 'intercompany.trading.parameter'
    _description = 'Intercompany Trading Parameter'

    source_company_id = fields.Many2one(
        'res.company', 
        string='Source Company', 
        required=True, 
    )

    destination_vendor_id = fields.Many2one(
        'res.partner', 
        string='Destination Vendor', 
    )

    intercompany_sale_destination_company_ids = fields.One2many(
        'intercompany.trading.destination.parameter', 
        'intercompany_trading_parameter_id',
        domain=[('parameter_type', '=', 'sale')]
    )

    intercompany_purchase_destination_company_ids = fields.One2many(
        'intercompany.trading.destination.parameter', 
        'intercompany_trading_parameter_id',
        domain=[('parameter_type', '=', 'purchase')]
    )

class IntercompanyTradingDestinationParameter(models.Model):
    _name = 'intercompany.trading.destination.parameter'
    _description = 'Intercompany Trading Destination Parameter'

    intercompany_trading_parameter_id = fields.Many2one('intercompany.trading.parameter', 
                                                       string='Intercompany Trading Source Parameter', 
                                                       required=True, 
                                                       ondelete='cascade'
                                                       )

    parameter_type = fields.Selection([
        ('sale', 'Sale Order'),
        ('purchase', 'Purchase Order'),
    ], string='Parameter Type', required=True, default='sale')

    intercompany_source_company_id = fields.Many2one(
        'res.company',
        string='Source Company',
        related='intercompany_trading_parameter_id.source_company_id',
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
    )
    

    category_ids = fields.Many2many(
        'sku.type.master', 
        string='Categories',
    )

    available_sku_category_ids = fields.Many2many(
        'sku.type.master',
        compute="_compute_available_categories",
    )

    tag_ids = fields.Many2many(
        'crm.tag',
        string='Tags',
    )

    #Deprecared: Needs to be removed
    destination_invoice_account_id = fields.Many2one(
        'account.account', 
        string='Destination Invoice Account', 
        domain="[('company_id', '=', destination_company_id), ('deprecated', '=', False)]"
    )

    #Deprecared: Needs to be removed
    destination_bill_account_id = fields.Many2one(
        'account.account', 
        string='Destination Bill Account', 
        domain="[('company_id', '=', destination_company_id), ('deprecated', '=', False)]"
    )

    default_reference = fields.Char(String="Default Reference")
    default_bci_project_id = fields.Char(String="Default BCI Project ID")
    tax_id = fields.Many2one(
        'account.tax',
        string='Default Tax',
        domain="['&', ('company_id', '=', destination_company_id), ('type_tax_use', 'not in', [parameter_type, False])]" 
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

class TradingSaleOrder(models.Model):
    _inherit = 'sale.order'

    intercompany = fields.Boolean(
        string='Intercompany Trading',
        default=False,
        help='Check this box to enable intercompany trading'
    )

    source_company_id = fields.Many2one(
        'res.company',
        string='Source Company',
    )

    destination_company_id = fields.Many2one(
        'res.company',
        string='Destination Company',
    )

    allowed_partner_ids = fields.Many2many('res.partner', compute='_compute_allowed_partner_ids')
    auto_created_sale_order = fields.Boolean(
        store=True,
        default=False,
    )

    def add_histroy_comment(self, subject, message_body):
        self.message_post(
            body=Markup(message_body),
            subject=subject,
            message_type='comment',
            subtype_xmlid='mail.mt_note'
        )


    @api.depends('intercompany')
    def _compute_allowed_partner_ids(self):
        for record in self:
            if record.intercompany and record.source_company_id:
                params = self.env['intercompany.trading.parameter'].search([
                    ('source_company_id', '=', self.source_company_id.id)
                ])
                record.allowed_partner_ids = params.mapped('intercompany_sale_destination_company_ids.source_customer_id').ids
                
            else:
                partner_domain = [
                    '|',
                    ('company_id', '=', self.env.company.id),
                    ('company_id', '=', False),
                ]
                partners = self.env['res.partner'].sudo().search(partner_domain)
                record.allowed_partner_ids = partners

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
        intercompany_param = self.env['intercompany.trading.parameter'].search(
                [('source_company_id', '=', self.source_company_id.id)],
                limit=1
            )
        if not intercompany_param:
            self.destination_company_id = False
            return

        destination_param = intercompany_param.intercompany_sale_destination_company_ids.filtered(
            lambda r: r.source_customer_id.id == self.partner_id.id
        )
            
        if self.partner_id and destination_param:
            self.destination_company_id = destination_param[0].destination_company_id.id

        else:
            self.destination_company_id = False

    def _register_payment_for_invoice(self, invoice):
        effective_date_val = invoice.date or fields.Date.today() 

        payment_data = {
            'amount': invoice.amount_residual,
            'journal_id': self.env['account.journal'].search([
                ('type', '=', 'bank'), 
                ('company_id', '=', invoice.company_id.id)
            ], limit=1).id,
            'payment_method_line_id': self.env['account.payment.method.line'].search([
                ('code', '=', 'manual'), 
                ('payment_type', '=', 'inbound')
            ], limit=1).id,
            'payment_date': effective_date_val, 
            'communication': invoice.name, 
        }
        
        payment_wizard = self.env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=invoice.ids,
        ).create(payment_data)
        
        payment_wizard.action_create_payments()

    def _register_payment_for_bill(self, bill, destination_company_id):
        effective_date_val = bill.invoice_date or fields.Date.today() 
        journal_id = self.env['account.journal'].search([
                ('type', '=', 'bank'), 
                ('company_id', '=', destination_company_id.id)
            ], limit=1).id
        outbound = self.env['account.payment.method.line'].search([
                ('code', '=', 'manual'), 
                ('payment_type', '=', 'outbound'),
                ('journal_id', '=', journal_id)
            ])
        payment_data = {
            'amount': bill.amount_residual,
            'journal_id': journal_id,
            'payment_method_line_id': outbound.id,
            'payment_date': effective_date_val, 
            'communication': bill.name,
            'partner_id': bill.partner_id.id,
        }
        payment_wizard = self.env['account.payment.register'].with_company(destination_company_id.id).with_context(
            active_model='account.move',
            active_ids=bill.ids,
        ).create(payment_data)
        
        payment_wizard.action_create_payments()

    def action_confirm(self):
        res = super(TradingSaleOrder, self).action_confirm()
        
        for order in self:
            if order.intercompany:
                deliveries = self.env['stock.picking'].search([('sale_id', '=', order.id), ('state', '!=', 'done')])
                
                for delivery in deliveries:
                    for move in delivery.move_ids_without_package:
                        move.quantity = move.product_uom_qty
                    
                    delivery.button_validate()
                    
                invoices = order._create_invoices(final=True)
                
                for invoice in invoices:
                    invoice.action_post()
                    self._register_payment_for_invoice(invoice=invoice)
                    
                purchase_order = self._create_purchase_order_from_sale_order(order)

                message_body = f"""
                    <p>Intercompany Purchase Order Created</p>
                    <ul>
                        <li><strong>Source company:</strong> <a href="#" data-oe-id="{self.source_company_id.id}" data-oe-model="account.move">{self.source_company_id.name}</a></li>
                        <li><strong>Destination Company:</strong> {order.destination_company_id.name}</li>
                        <li><strong>Connected Intercompany Purchase Order:</strong> {purchase_order.name}</li>
                    </ul>
                """

                self.add_histroy_comment(subject="Sale Order Created", message_body=message_body)
                
        return res
    
    def get_first_id(self, recordset):
        return recordset[0].id if recordset else False
    
    def _create_purchase_order_from_sale_order(self, sale_order):
        ic_param = self.env['intercompany.trading.parameter'].sudo().search([
            ('source_company_id', '=', sale_order.source_company_id.id),
        ], limit=1)

        if not ic_param:
            raise UserError("Could not find Intercompany parameters for the source company.")

        source_param = ic_param.intercompany_sale_destination_company_ids.filtered(
            lambda r: r.source_customer_id.id == sale_order.partner_id.id
        )

        if not source_param:
             raise UserError("Could not find destiantion company parameters for the source company")


        vendor = source_param.destination_vendor_id

        first_brand_id = sale_order.get_first_id(source_param.brand_ids)
        first_category_id = sale_order.get_first_id(source_param.category_ids)
        first_tag_id = sale_order.get_first_id(source_param.tag_ids)

        purchase_order_lines = []
        for line in sale_order.order_line:
            purchase_order_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'product_uom': line.product_uom.id,
                'product_qty': line.product_uom_qty,
                'qty_invoiced': line.product_uom_qty,
                'price_unit': line.price_unit, 
                'name': line.name,
                'taxes_id': [(6, 0, [source_param.tax_id.id])] if source_param.tax_id else False,
            }))

        purchase_order_vals = {
            'company_id': sale_order.destination_company_id.id,
            'partner_id': vendor.id,
            'origin': sale_order.name, 
            'order_line': purchase_order_lines,
            'payment_term_id': sale_order.payment_term_id.id,
            'brand_id': first_brand_id,
            'category_ids': [(6, 0, [first_category_id])] if first_category_id else False,
            'tag_ids': [(6, 0, [first_tag_id])] if first_tag_id else False,
        }

        new_po = self.env['purchase.order'].create(purchase_order_vals)
        new_po.button_confirm()
        new_po.picking_ids.sudo().with_context(
            skip_journal=True,
        ).button_validate()
        new_po.action_create_invoice()
        for bill in new_po.invoice_ids:
            bill.write({
                'invoice_date': fields.Date.today(), 
            })
            bill.action_post()
            self._register_payment_for_bill(bill, sale_order.destination_company_id)

        return new_po

class SaleOrderLineInheritCustom(models.Model):
    _inherit = 'sale.order.line'
                
    @api.onchange('product_id', 'order_id')
    def _onchange_product_id_check_intercompany(self):
        _logger.info(f"======= ONCHANGE Fired. Product Type: {self.product_id.type}")
        
        if self.order_id.intercompany and self.product_id.type == 'service':
            
            self.product_id = False
            
            return {
                'warning': {
                    'title': _("Validation Error!"),
                    'message': _("You can only use storable products for intercompany trading."),
                }
            }
        

##### Purchase Order #####
class TradingPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    intercompany_trading = fields.Boolean(
        string='Intercompany Trading',
        default=False,
        help='Check this box to enable intercompany trading'
    )

    source_company_id = fields.Many2one(
        'res.company',
        string='Source Company',
    )

    destination_company_id = fields.Many2one(
        'res.company',
        string='Destination Company',
    )

    allowed_partner_ids = fields.Many2many('res.partner', compute='_compute_allowed_partner_ids')
    auto_created_sale_order = fields.Boolean(
        store=True,
        default=False,
    )

    def add_histroy_comment(self, subject, message_body):
        self.message_post(
            body=Markup(message_body),
            subject=subject,
            message_type='comment',
            subtype_xmlid='mail.mt_note'
        )

    @api.depends('intercompany_trading')
    def _compute_allowed_partner_ids(self):
        for record in self:
            if record.intercompany_trading and record.source_company_id:
                params = self.env['intercompany.trading.parameter'].search([
                    ('source_company_id', '=', self.source_company_id.id)
                ])
                record.allowed_partner_ids = params.mapped('intercompany_purchase_destination_company_ids.source_customer_id').ids
                
            else:
                partner_domain = [
                    '|',
                    ('company_id', '=', self.env.company.id),
                    ('company_id', '=', False),
                ]
                partners = self.env['res.partner'].sudo().search(partner_domain)
                record.allowed_partner_ids = partners

    @api.onchange('intercompany_trading')
    def _onchange_set_customer_partner_id(self):
        if not self.intercompany_trading:
            self.source_company_id = False
        
        elif self.intercompany_trading:
            self.source_company_id = self.env.company.id
            self.set_destination_company()

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.intercompany_trading and self.partner_id and self.source_company_id:
            self.set_destination_company()
        elif not self.intercompany_trading:
            self.destination_company_id = False

    def set_destination_company(self):
        destination_param = False
        intercompany_param = self.env['intercompany.trading.parameter'].search(
                [('source_company_id', '=', self.source_company_id.id)],
                limit=1
            )
        if not intercompany_param:
            self.destination_company_id = False
            return

        destination_param = intercompany_param.intercompany_purchase_destination_company_ids.filtered(
            lambda r: r.source_customer_id.id == self.partner_id.id
        )
            
        if self.partner_id and destination_param:
            self.destination_company_id = destination_param[0].destination_company_id.id

        else:
            self.destination_company_id = False

    def _register_payment_for_invoice(self, invoice, destination_company):
        effective_date_val = invoice.date or fields.Date.today()
        journal_id = self.env['account.journal'].search([
                ('type', '=', 'bank'), 
                ('company_id', '=', destination_company.id)
            ], limit=1).id
        payment_method = self.env['account.payment.method.line'].search([
                ('code', '=', 'manual'), 
                ('payment_type', '=', 'inbound'),
                ('journal_id', '=', journal_id)
            ])
        payment_data = {
            'amount': invoice.amount_residual,
            'journal_id': journal_id,
            'payment_method_line_id': payment_method.id,
            'payment_date': effective_date_val,
            'communication': invoice.name, 
        }
        
        payment_wizard = self.env['account.payment.register'].with_company(destination_company.id).with_context(
            active_model='account.move',
            active_ids=invoice.ids,
        ).create(payment_data)
        
        payment_wizard.action_create_payments()

    def _register_payment_for_bill(self, bill):
        effective_date_val = bill.invoice_date or fields.Date.today() 
        journal_id = self.env['account.journal'].search([
                ('type', '=', 'bank'), 
                ('company_id', '=', bill.company_id.id)
            ], limit=1).id
        outbound = self.env['account.payment.method.line'].search([
                ('code', '=', 'manual'), 
                ('payment_type', '=', 'outbound'),
                ('journal_id', '=', journal_id)
            ])
        payment_data = {
            'amount': bill.amount_residual,
            'journal_id': journal_id,
            'payment_method_line_id': outbound.id,
            'payment_date': effective_date_val, 
            'communication': bill.name, 
        }
        
        payment_wizard = self.env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=bill.ids,
        ).create(payment_data)
        
        payment_wizard.action_create_payments()

    def button_confirm(self):
        res = super(TradingPurchaseOrder, self).button_confirm()
        
        for order in self:
            if order.intercompany_trading:
                deliveries = self.env['stock.picking'].search([('purchase_id', '=', order.id), ('state', '!=', 'done')])
                
                for delivery in deliveries:
                    delivery.button_validate()
                    
                bill_action = order.action_create_invoice()

                if bill_action and isinstance(bill_action, dict) and bill_action.get('res_id'):
                    vendor_bill = self.env['account.move'].browse(bill_action['res_id'])
                    if not vendor_bill.invoice_date:
                        vendor_bill.invoice_date = fields.Date.today()
                    vendor_bill.action_post()

                    if vendor_bill.state == 'posted' and vendor_bill.amount_residual > 0:
                        self._register_payment_for_bill(vendor_bill)
                    
                sale_order = self._create_sale_order_from_purchase_order(order)

                message_body = f"""
                    <p>Intercompany Purchase Order Created</p>
                    <ul>
                        <li><strong>Source company:</strong> <a href="#" data-oe-id="{self.source_company_id.id}" data-oe-model="account.move">{self.source_company_id.name}</a></li>
                        <li><strong>Destination Company:</strong> {order.destination_company_id.name}</li>
                        <li><strong>Connected Intercomapny Trading Sale Order:</strong> {sale_order.name}</li>
                    </ul>
                """

                self.add_histroy_comment(subject="Purchase Order Created", message_body=message_body)
                
        return res
    
    def get_first_id(self, recordset):
        return recordset[0].id if recordset else False
    
    def _create_sale_order_from_purchase_order(self, purchase_order):
        ic_param = self.env['intercompany.trading.parameter'].sudo().search([
            ('source_company_id', '=', purchase_order.source_company_id.id),
        ], limit=1)

        if not ic_param:            
            raise UserError("Could not find the intercompany parameters for the source company")

        source_param = ic_param.intercompany_purchase_destination_company_ids.filtered(
            lambda r: r.source_customer_id.id == purchase_order.partner_id.id
        )

        if not source_param:
             raise UserError("Did not find the destination parameter for this vendor")


        vendor = source_param.destination_vendor_id

        first_brand_id = purchase_order.get_first_id(source_param.brand_ids)
        first_category_id = purchase_order.get_first_id(source_param.category_ids)
        first_tag_id = purchase_order.get_first_id(source_param.tag_ids)

        sale_order_lines = []
        for line in purchase_order.order_line:
            sale_order_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'product_uom': line.product_uom.id,
                'product_uom_qty': line.product_uom_qty,
                'qty_invoiced': line.product_uom_qty,
                'price_unit': line.price_unit, 
                'name': line.name,
                'tax_id': [(6, 0, [source_param.tax_id.id])] if source_param.tax_id else False,
            }))

        sale_order_vals = {
            'company_id': purchase_order.destination_company_id.id,
            'partner_id': vendor.id,
            'reference': source_param.default_reference,
            'bci_project': source_param.default_bci_project_id,
            'origin': purchase_order.name, 
            'order_line': sale_order_lines,
            'payment_term_id': purchase_order.payment_term_id.id,
            'brand_id': first_brand_id,
            'category_ids': [(6, 0, [first_category_id])] if first_category_id else False,
            'tag_ids': [(6, 0, [first_tag_id])] if first_tag_id else False,
        }

        new_sale_order = self.env['sale.order'].create(sale_order_vals)
        new_sale_order.action_confirm()
        
        new_sale_order.picking_ids.sudo().with_context(
            skip_journal=True,
        ).button_validate()

        invoices = new_sale_order._create_invoices(final=True)
        for invoice in invoices:
            invoice.action_post()
            self._register_payment_for_invoice(invoice, purchase_order.destination_company_id)

        return new_sale_order


class PurchaseOrderLineInheritCustom(models.Model):
    _inherit = 'purchase.order.line'
                
    @api.onchange('product_id', 'order_id')
    def _onchange_product_id_check_intercompany(self):
        _logger.info(f"======= ONCHANGE Fired. Product Type: {self.product_id.type}")
        
        if self.order_id.intercompany_trading and self.product_id.type == 'service':
            
            self.product_id = False
            
            return {
                'warning': {
                    'title': _("Validation Error!"),
                    'message': _("You can only use storable products for intercompany trading."),
                }
            }