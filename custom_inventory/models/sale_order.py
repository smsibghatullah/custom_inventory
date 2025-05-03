from unicodedata import category

from odoo import models, fields, api,_
from odoo.exceptions import UserError,ValidationError
import base64
from odoo.fields import Command
import random
from collections import defaultdict


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    brand_id = fields.Many2one(
        'brand.master', 
        string='Brand *',
         required=True,
          domain="[('company_id', '=', company_id)]",
        help='Select the brand associated with this sale order'
    )

    category_ids = fields.Many2many(
        'sku.type.master',
        'sale_category_rel',
        'product_id',
        'category_id',
        string='Categories *',
         required=True,
        help='Select the Categories associated with the selected brand'
    )

    text_fields = fields.One2many('dynamic.field.text', 'sale_order_id', compute="_compute_text_field", inverse="_inverse_text_field", store=True )
    checkbox_fields = fields.One2many('dynamic.field.checkbox', 'sale_order_id', compute="_compute_checkbox_field", inverse="_inverse_checkbox_field", store=True)
    selection_fields = fields.One2many('dynamic.saleorder.selection.key', 'sale_order_id', compute="_compute_selection_field", inverse="_inverse_selection_field", store=True)
    revision_number = fields.Char('')
    revision_number_count = fields.Integer(compute="_compute_revision_number_count")
    terms_conditions = fields.Text(string='Brand Terms & Conditions')
    bom_id = fields.Many2one('bom.products', string='BOM',
     domain="[('brand_id', '=', brand_id)]"
    , help='Select the Bill of Materials')
    reference = fields.Char(string='Reference *')
    amount_without_shipping = fields.Float(
        string="Subtotal (Excluding Shipping)",
        compute="_compute_amount_without_shipping",
    )
    formatted_date_order = fields.Char(
        string="Formatted Order Date",
        compute="_compute_formatted_dates",
    )
    formatted_validity_date = fields.Char(
        string="Formatted Expiry Date",
        compute="_compute_formatted_dates",
    )
    discount_amount = fields.Monetary(
        string="Total Discount",
        compute="_compute_discount_amount",
        currency_field="currency_id"
    )
    is_tag_access = fields.Boolean(compute="_compute_tag_access")
    has_text_fields = fields.Boolean(compute="_compute_has_text_fields", store=True)
    has_checkbox_fields = fields.Boolean(compute="_compute_has_checkbox_fields", store=True)
    has_selection_fields = fields.Boolean(compute="_compute_has_selection_fields", store=True)
    has_tag_required = fields.Boolean(compute="_compute_has_tag_required", store=True)
    available_tag_ids = fields.Many2many(
        'crm.tag',
        compute="_compute_available_tags",
    )
    available_sku_category_ids = fields.Many2many(
        'sku.type.master',
        compute="_compute_available_categories",
    )
    bci_project = fields.Char(string='BCI Project')
    customer_description = fields.Char(string="Customer Description")

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.customer_description = self.partner_id.name
        else:
            self.customer_description = False


    @api.depends("tag_ids")
    def _compute_available_tags(self):
        for record in self:
            record.available_tag_ids = self.env.user.tag_ids
            print(record.available_tag_ids,"ppppppppppppppppppppppppmubeenpssssssssssssssssssssssssss")
    @api.depends("category_ids")
    def _compute_available_categories(self):
        for record in self:
            record.available_sku_category_ids = self.env.user.sku_category_ids
            print(record.available_sku_category_ids,"ppppppppppppppppppppppppmubeenpssssssssssssssssssssssssss")
         

    @api.depends("brand_id", "brand_id.is_tag_show")
    def _compute_has_tag_required(self):
        for record in self:
            record.has_tag_required = bool(record.brand_id.is_tag_show)
            
    @api.depends('text_fields')
    def _compute_has_text_fields(self):
        for record in self:
            record.has_text_fields = bool(record.text_fields)

    @api.depends('checkbox_fields')
    def _compute_has_checkbox_fields(self):
        for record in self:
            record.has_checkbox_fields = bool(record.checkbox_fields)

    @api.depends('selection_fields')
    def _compute_has_selection_fields(self):
        for record in self:
            record.has_selection_fields = bool(record.selection_fields)

    @api.depends("brand_id")
    def _compute_tag_access(self):
        for record in self:
            record.is_tag_access = record.brand_id.is_tag_show if record.brand_id else False
    
    @api.onchange('brand_id')
    def _onchange_brand_id(self):
        self.bom_id = False  
        return {'domain': {'bom_id': [('brand_id', '=', self.brand_id.id)]}}



    @api.depends("order_line.price_subtotal", "order_line.discount")
    def _compute_discount_amount(self):
        for order in self:
            total_discount = 0
            for line in order.order_line:
                total_discount += (line.price_unit * line.product_uom_qty * line.discount / 100)
            
            order.discount_amount = total_discount

    def _compute_formatted_dates(self):
        for order in self:
            
            print('ppppppppppppppppppppppppppppppppppppppp')
            order.formatted_date_order = order.date_order.strftime("%d-%b-%Y") if order.date_order else ""
            order.formatted_validity_date = order.validity_date.strftime("%d-%b-%Y") if order.validity_date else ""
            print(order.formatted_validity_date,order.formatted_date_order,"mmmmmmmmmmmmmmmmmmmmmmmnnnnnnnnnnnnnnnnnnmmmmmmmmmmmmmmm")

    @api.onchange('date_order','validity_date')
    def _compute_formatted_dates_onchange(self):
        for order in self:
            order.available_tag_ids = self.env.user.tag_ids
            order.available_sku_category_ids = self.env.user.sku_category_ids
            print(order.available_tag_ids,'yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy')
            order.formatted_date_order = order.date_order.strftime("%d-%b-%Y") if order.date_order else ""
            order.formatted_validity_date = order.validity_date.strftime("%d-%b-%Y") if order.validity_date else ""
            print(order.formatted_validity_date,order.formatted_date_order,"mmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmm")

    @api.depends("amount_untaxed", "carrier_id.fixed_price")
    def _compute_amount_without_shipping(self):
        for order in self:
            order.amount_without_shipping = order.amount_untaxed - (order.carrier_id.fixed_price or 0.0)

    @api.model
    def create(self, vals):
        order = super(SaleOrder, self).create(vals)
        print(order.amount_total,"mmmmmmmmmmmmmmmmmmmmmmmmmm")
        if not self.env.context.get('skip_validation'):
            for item in order.text_fields:
                    if item.validation_check and not item.text_value:
                        raise ValidationError(f"The field '{item.text_field}' requires a value.")
        if order.amount_total == 0:
                raise ValidationError("The Sale Order total amount cannot be zero.")
        if 'reference' in vals:
            user = self.env.user
            order.message_post(
                body=f"Sale Order with Reference: {order.reference}",
                message_type='notification',
                author_id=user.partner_id.id
            )
        
        return order

    @api.model
    def write(self, vals):
        result = super(SaleOrder, self).write(vals)
        print(self.amount_total,"mmmmmmmmccccmmmmmmmmmmmmmmmmmm")
        for order in self:
            if not self.env.context.get('skip_validation'):
                for item in order.text_fields:
                    if item.validation_check and not item.text_value:
                        raise ValidationError(f"The field '{item.text_field}' requires a value.")
            if order.amount_total == 0:
                raise ValidationError("The Sale Order total amount cannot be zero.")
        if 'reference' in vals:
            user = self.env.user
            for order in self:
                order.message_post(
                    body=f"Sale Order with Reference: {order.reference}",
                    message_type='notification',
                    author_id=user.partner_id.id
                )
        
        return result

    def _validate_text_fields(self):
            """Check if required text fields (where validation_check=True) have values."""
            for record in self.text_fields:
                print(record.validation_check,"kkkkkkkkkkkkkkkkkkkkkkkkkkkk",record.text_value)
                if record.validation_check and not record.text_value:
                    raise ValidationError(_("The field '%s' is required. Please fill the value.") % record.text_field)


    @api.onchange('bom_id')
    def _onchange_bom_id(self):
        if self.bom_id:
            self.order_line = [(5, 0, 0)]  
            new_lines = []
            for line in self.bom_id.line_product_ids:
                new_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'product_template_id': line.product_id.product_tmpl_id,
                    'product_uom_qty': line.product_uom_qty,
                    'name': line.product_id.name,
                    'price_unit': line.product_id.lst_price,
                }))
            self.order_line = new_lines

    def _inverse_text_field(self):
        for line in self:
            for item in line.text_fields:
                # Update the sale_order_id on the corresponding text field
                item.sale_order_id = line.id

    def _inverse_checkbox_field(self):
        for line in self:
            for item in line.checkbox_fields:
                # Update the sale_order_id on the corresponding text field
                item.sale_order_id = line.id

    def _inverse_selection_field(self):
        for line in self:
            for item in line.selection_fields:
                # Update the sale_order_id on the corresponding text field
                item.sale_order_id = line.id

    @api.depends('brand_id')
    def _compute_text_field(self):
        for line in self:
            if line.brand_id:
                copied_text_fields = []
                if line.brand_id.text_fields:
                    for item in line.brand_id.text_fields:
                        copied_item = item.copy({
                            'sale_order_id': line.id,
                            'brand_id': False
                        })
                        copied_text_fields.append(copied_item.id)
                line.text_fields = [(6, 0, copied_text_fields)]
            else:
                line.text_fields = [(5, 0, 0)]
                line.category_ids  = [(6, 0, [])]

    @api.depends('brand_id')
    def _compute_checkbox_field(self):
        for line in self:
            if line.brand_id:
                copied_checkbox_fields = []

                for item in line.brand_id.checkbox_fields:
                    copied_checkbox_fields.append(item.copy({
                        'sale_order_id': line.id,
                        'brand_id': False  # Clear the brand_id field
                    }).id)
                line.checkbox_fields = [(6, 0, copied_checkbox_fields)]
                # line.sku_ids  = [(6, 0, [])]



    @api.depends('brand_id')
    def _compute_selection_field(self):
        for line in self:
            selection_fields = []
            random_number = random.randint(100000, 999999)
            if line.brand_id:
                for item in line.brand_id.selection_fields:
                    selection_id = self.env['dynamic.saleorder.selection.key'].create({
                        'selection_field': item.selection_field,
                        'sale_order_id': line.id,
                        'sale_random_key': random_number
                    })
                    
                    for value in item.selection_value:
                        new_option = self.env['dynamic.field.selection.values.sale'].create({
                            'value_field': value.value_field,
                            'key_field': selection_id.id,
                            'key_field_parent': item.selection_field
                        })
                        
                    if not selection_id.selected_value:
                        selection_id.selected_value = new_option
                    selection_fields.append(selection_id.id)
            line.selection_fields = [(6, 0, selection_fields)]


    @api.depends('revision_number')
    def _compute_revision_number_count(self):
        for item in self:
            # print( self.search_count([('revision_number','=',item.revision_number)]))
            # print('ssssssssssssssssssssssssssssssss')
            if item.revision_number:
                item.revision_number_count = self.search_count([('revision_number','=',item.revision_number)])
            else:
                item.revision_number_count = 0

    def action_view_revisions(self):
        self.ensure_one()
        source_orders = self.search([('revision_number','=',self.revision_number)])
        view_tree = self.env.ref('sale.view_quotation_tree_with_onboarding')
        view_from = self.env.ref('sale.view_order_form')
        return {
            'name': _('Revision'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form,tree',
            'domain': [('id', 'in', source_orders.ids)],
            'res_model': 'sale.order',
            'views': [[view_tree.id, "list"],[view_from.id, "form"]],
            'target': 'self'
        }


    def action_revise_order(self):
        for item in self:
            if not item.revision_number:
                item.revision_number = item.name

            revision_number_count = self.search_count([('revision_number', '=', item.revision_number)])
            new_item = item.with_context(skip_validation=True).copy()

            new_item.name = f"{item.revision_number}-{revision_number_count}"
            item.action_cancel()

            return {
                'type': 'ir.actions.act_window',
                'name': 'Revised Order',
                'view_mode': 'form',
                'res_model': self._name,
                'res_id': new_item.id,
                'target': 'current',
            }

    # @api.onchange('brand_id')
    # def _onchange_text_fields(self):
    #     for line in self:
    #         line.sku_ids = False
    #         line.terms_conditions = line.brand_id.terms_conditions
    #         line.text_fields.unlink()
    #         # print('22222222222222222')
    #         random_number = random.randint(100000, 999999)
    #         if line.brand_id:
    #             print( line.brand_id)
    #             # category_ids = self.env['sku.type.master'].search([('brand_id','=',line.brand_id.id)]).ids
                # print(category_ids,"category_ids")
                # print(line.brand_id.checkbox_fields)
                # print("00000000000000000000000000000")
                # copied_text_fields = []
                # checkbox_fields = []
                # selection_fields = []
                # for item in line.brand_id.text_fields:
                #     copied_text_fields.append(item.copy({
                #         'sale_order_id': line.id,
                #         'brand_id': False  # Clear the brand_id field
                #     }).id)
                # # print(copied_text_fields, "copied_text_fields 11111111111111111111111111----")
                # for item in line.brand_id.checkbox_fields:
                #     copied_item = item.copy({
                #         'sale_order_id': line.id,
                #         'brand_id': False  # Clear the brand_id field
                #     }).id
                #     # copied_item.brand_id , "aaaaaaaaaaaaaaaaaaaaaa new "
                #     checkbox_fields.append(copied_item)
                # op_key = '00000'
                # for item in line.brand_id.selection_fields:
                #     options = {}
                #     item_sale_item_selection = {'selection_field': item.selection_field,
                #     'sale_order_id':line.id}
                #     selection_id = self.env['dynamic.saleorder.selection.key'].create(item_sale_item_selection)
                #     for value in item.selection_value:
                #         # print(item.selection_field,"item.selection_field")
                #         options = {'key_field_parent':item.selection_field, 'value_field':value.value_field
                #         , 'sale_order_no': random_number,'key_field':selection_id.id}
                #         # print (options,"options")
                #         self.env['dynamic.field.selection.values.sale'].create(options)
                #     selection_fields.append(selection_id.id)
                # print(checkbox_fields ,"checkbox_fields")
                # print(selection_fields, "selection_fields")
                # line.text_fields = copied_text_fields
                # line.checkbox_fields = checkbox_fields #line.brand_id.checkbox_fields.ids
                # line.selection_fields = selection_fields #line.brand_id.selection_fields.ids
                # line.sku_ids = [(6, 0, category_ids)]
            #     return  {'domain': {'text_fields': copied_text_fields, 'checkbox_fields': checkbox_fields,
            #                         'selection_fields':selection_fields }}
            # else:
            #     return {'domain': {'text_fields': [], 'sku_ids': [],
            #                        'checkbox_fields': [],
            #                        'selection_fields': []}}



    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()

        values = {
            'ref': self.client_order_ref or '',
            'move_type': 'out_invoice',
            'narration': self.note,
            'currency_id': self.currency_id.id,
            'campaign_id': self.campaign_id.id,
            'medium_id': self.medium_id.id,
            'source_id': self.source_id.id,
            'team_id': self.team_id.id,
            'partner_id': self.partner_invoice_id.id,
            'partner_shipping_id': self.partner_shipping_id.id,
            'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id._get_fiscal_position(self.partner_invoice_id)).id,
            'invoice_origin': self.name,
            'invoice_payment_term_id': self.payment_term_id.id,
            'invoice_user_id': self.user_id.id,
            'payment_reference': self.reference ,
            'transaction_ids': [Command.set(self.transaction_ids.ids)],
            'company_id': self.company_id.id,
            'invoice_line_ids': [],
            'user_id': self.user_id.id,
            'brand_id': self.brand_id.id,
            'category_ids': [(6, 0, self.category_ids.ids)],
            'bom_id': self.bom_id.id,
            'terms_conditions': self.brand_id.terms_conditions_invoice,
            'reference': self.reference,
            'tag_ids':[(6, 0, self.tag_ids.ids)],
            'customer_description':self.customer_description
        }
        if self.journal_id:
            values['journal_id'] = self.journal_id.id
        return values


    @api.onchange('brand_id')
    def _onchange_brand_id(self):
        if self.brand_id:
            matched_categories = self.env['sku.type.master'].search([
                ('brand_id', '=', self.brand_id.id),
                ('id', 'in', self.category_ids.ids)
            ])
            if not matched_categories:
                self.category_ids = [(6, 0, [])]
                self.order_line = [(6, 0, [])]
            self.terms_conditions = self.brand_id.terms_conditions
       
    def action_send_report_email(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Send Email',
            'res_model': 'sale.order.email.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_order_id': self.id,
                'default_recipient_email': self.partner_id.email,
                'default_subject': f'Sale Order {self.name}',
            },
        }

    def action_quotation_send(self):
        self.ensure_one()
        self.order_line._validate_analytic_distribution()
        lang = self.env.context.get('lang')

        children = self.partner_id.child_ids
      
        ctx = {
            'default_model': 'sale.order',
            'default_custom_email_from': self.brand_id.so_email,
            'default_res_ids': self.ids,
            'default_template_id': self.brand_id.mail_sale_quotation_template_id.id if self.brand_id.mail_sale_quotation_template_id else None,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'default_email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
            'proforma': self.env.context.get('proforma', False),
            'force_email': True,
            'model_description': self.with_context(lang=lang).type_name,
            'partner_child': self.partner_id.child_ids.ids,
        }

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }


    def action_sale_order_send(self):
        """ Opens a wizard to compose an email, with relevant mail template loaded by default """
        self.ensure_one()
        self.order_line._validate_analytic_distribution()
        lang = self.env.context.get('lang')
        # mail_template = self._find_mail_template()
        # if mail_template and mail_template.lang:
        #     lang = mail_template._render_lang(self.ids)[self.id]
        ctx = {
            'default_model': 'sale.order',
             'partner_child': self.partner_id.child_ids.ids,
            'default_custom_email_from' : self.brand_id.so_email ,
            'default_res_ids': self.ids,
            'default_template_id': self.brand_id.mail_sale_template_id.id if self.brand_id.mail_sale_template_id else None,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'default_email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
            'proforma': self.env.context.get('proforma', False),
            'force_email': True,
            'model_description': self.with_context(lang=lang).type_name,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }

    @api.onchange('pricelist_id')
    def _onchange_pricelist_id(self):
        """
        Update all order lines when the pricelist is changed.
        """
        for order in self:
            for line in order.order_line:
                line._update_price_from_pricelist()
            
    def action_confirm(self):
        """Override sale order confirmation to mark the linked CRM Lead as 'Won'."""
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            if order.opportunity_id:
                won_stage = self.env['crm.stage'].search([('is_won', '=', True)], limit=1)
                if won_stage:
                    order.opportunity_id.write({'stage_id': won_stage.id})
        return res

    def create_journal_entry(self):
        for order in self:
            category_totals = defaultdict(lambda: {'debit': 0.0, 'credit': 0.0})
            category_accounts = {}
            product_cost = 0

            for line in order.order_line:
                category = line.product_id.categ_id

                if not category:
                    continue

                if category.id not in category_accounts:
                    debit_account = category.sale_debit_account_id
                    credit_account = category.sale_credit_account_id
                    sale_journal = category.sale_journal_id

                    if not debit_account or not credit_account or not sale_journal:
                        raise UserError(f"Please configure Sale Debit Account, Credit Account, and Journal in category '{category.name}'.")

                    category_accounts[category.id] = {
                        'debit_account': debit_account,
                        'credit_account': credit_account,
                        'journal': sale_journal
                    }

                category_totals[category.id]['debit'] += line.product_id.standard_price
                category_totals[category.id]['credit'] += line.product_id.standard_price
                product_cost += line.product_id.standard_price

            move_lines = []

            for category_id, totals in category_totals.items():
                accounts = category_accounts[category_id]
                
                move_lines.append((0, 0, {
                    'account_id': accounts['debit_account'].id,
                    'debit': totals['debit'],
                    'credit': 0.0,
                    'name': f"Sale Order {order.name} - {self.env['product.category'].browse(category_id).name} - Debit",
                }))

                move_lines.append((0, 0, {
                    'account_id': accounts['credit_account'].id,
                    'debit': 0.0,
                    'credit': totals['credit'],
                    'name': f"Sale Order {order.name} - {self.env['product.category'].browse(category_id).name} - Credit",
                }))

            delivery_order = self.env['stock.picking'].search([
                ('origin', '=', order.name),
                ('picking_type_id.code', '=', 'outgoing')  
            ], limit=1)

            reference = f"{delivery_order.name if delivery_order else 'No Delivery'} ({order.name})"
            print(move_lines,"ppppppppppppppppppppppppppssssss")
            

            move = self.env['account.move'].create({
                'brand_id': self.brand_id.id,
                'category_ids': [(6, 0, self.category_ids.ids)],
                'bom_id': self.bom_id.id,
                'terms_conditions': self.brand_id.terms_conditions_invoice,
                'reference': self.reference,
                'tag_ids':[(6, 0, self.tag_ids.ids)],
                'journal_id': next(iter(category_accounts.values()))['journal'].id,  
                'date': fields.Date.context_today(self),
                'ref': reference,
                'line_ids': move_lines,
            })
            print(move.line_ids,product_cost,"ppppppppppppppppppppppppppssssss")
            # 9/0
            move.action_post()
            line.product_id.standard_price = product_cost
    

class SaleOrderEmailWizard(models.TransientModel):
    _name = 'sale.order.email.wizard'
    _description = 'Sale Order Email Wizard'

    sale_order_id = fields.Many2one('sale.order', string='Sale Order', required=True, readonly=True)
    recipient_email = fields.Char(string='Recipient Email', required=True)
    subject = fields.Char(string='Subject', required=True, default='Sale Order Report')
   

    def action_send_email(self):
        self.ensure_one()

        sale_order = self.env['sale.order'].browse(self.env.context.get('active_id'))
        if not sale_order:
            raise UserError(_("No Sale Order found to generate the email."))

        report_name = 'sale.report_saleorder'

        try:
            pdf_content, content_type = self.env['ir.actions.report']._render_qweb_pdf(
                report_name, [sale_order.id]
            )

            pdf_base64 = base64.b64encode(pdf_content)
            attachment = self.env['ir.attachment'].create({
                'name': f"{sale_order.name}.pdf",
                'type': 'binary',
                'datas': pdf_base64,
                'res_model': 'sale.order',
                'res_id': sale_order.id,
                'mimetype': 'application/pdf',
            })
            from_email = self.sale_order_id.brand_id.so_email
            print(self.sale_order_id.brand_id.so_email,"dddddddddddddddddddddddddddd")
            if not from_email:
                raise UserError(_("No Sale Order email is set for the selected brand."))
            mail_values = {
                'subject': self.subject or f"Sale Order {sale_order.name}",
                'body_html': _('Please find attached your Sale Order.'),
                'email_from': from_email, 
                'email_to': self.recipient_email,
                'attachment_ids': [(6, 0, [attachment.id])],
            }
            mail = self.env['mail.mail'].create(mail_values)
            # mail.send()

        except Exception as e:
            raise UserError(_("An error occurred while generating the PDF: %s") % str(e))

        return {'type': 'ir.actions.act_window_close'}


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    category_ids = fields.Many2many(
        'sku.type.master',
        'sale_line_category_rel_we',
        'product_id',
        'category_id',
        string=' ',
        compute='_compute_product_sku_id',
        required=True,
        store=True,
        help='Select the Categories associated with the selected brand'
    )
    pricelist_id = fields.Many2one(
        'product.pricelist', 
        string="Pricelist", 
        related='order_id.pricelist_id', 
        store=True, 
        readonly=False
    )


    @api.onchange('product_id', 'pricelist_id')
    def _onchange_product_pricelist(self):
        for line in self:
            line._update_price_from_pricelist()

    def _update_price_from_pricelist(self):
        for line in self:
            if line.product_id and line.pricelist_id:
                for item in line.pricelist_id.item_ids:
                    if line.product_template_id == item.product_tmpl_id:
                        line.price_unit = item.fixed_price

    @api.onchange('product_id', 'product_uom_qty')
    def _check_available_quantity(self):
        for line in self:
            if line.product_id and line.product_id.type == 'product':
                # Get total available quantity in internal locations
                quants = self.env['stock.quant'].search([
                    ('product_id', '=', line.product_id.id),
                    ('location_id.usage', '=', 'internal')
                ])
                total_available_qty = sum(quants.mapped('available_quantity'))

                if line.product_uom_qty > total_available_qty:
                    return {
                        'warning': {
                            'title': 'Quantity Warning',
                            'message': (
                                f"Product: {line.product_id.display_name}\n"
                                f"Available quantity is only {total_available_qty:.2f}. "
                                f"You have entered {line.product_uom_qty:.2f}."
                            ),
                        }
                    }




    @api.model
    def create(self, vals):
        """
        Ensure price is set based on pricelist at creation.
        """
        record = super(SaleOrderLine, self).create(vals)
        return record

    @api.depends('order_id.category_ids')
    def _compute_product_sku_id(self):
        for line in self:
            print(f"Order ID: {line.order_id.id}, BOM ID: {line.order_id.bom_id}")
            print(f"Before Compute: {line.category_ids}")

            if not line.order_id.bom_id:
                if line.order_id and line.order_id.category_ids:
                    line.category_ids = line.order_id.category_ids.ids
            else:
                category_ids = self.env['sku.type.master'].search([]) 
                line.category_ids = category_ids

            print(f"After Compute: {line.category_ids}")


    @api.onchange('category_ids')
    def _onchange_category_ids(self):
        for line in self:
            return {'domain': {'product_id': [('category_ids', 'in', line.category_ids.ids), ('sale_ok', '=', True)]}}

    @api.onchange('product_id')
    def _compute_product_template_id(self):
        print('kkkkkkkkkkkkkkkkkkkkk')
        for line in self:
            if not line.order_id.bom_id:
                if line.order_id and line.order_id.category_ids:
                    line.category_ids = line.order_id.category_ids.ids
            else:
                category_ids = self.env['sku.type.master'].search([]) 
                line.category_ids = category_ids

            line.product_template_id = line.product_id.product_tmpl_id
            print("yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy")

class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.model
    def _compute_taxes_for_single_line(self, base_line, handle_price_include=True, include_caba_tags=False,
                                       early_pay_discount_computation=None, early_pay_discount_percentage=None):
        
        if base_line['record']._name == 'sale.order.line':
            if not base_line['record'][0].order_id.brand_id.is_tax_show:
                base_line['taxes'] = self.env['account.tax'].search([('id','=',0)])
        
        orig_price_unit_after_discount = base_line['price_unit'] * (1 - (base_line['discount'] / 100.0))
        price_unit_after_discount = orig_price_unit_after_discount
        taxes = base_line['taxes']._origin
        currency = base_line['currency'] or self.env.company.currency_id
        rate = base_line['rate']

        if early_pay_discount_computation in ('included', 'excluded'):
            remaining_part_to_consider = (100 - early_pay_discount_percentage) / 100.0
            price_unit_after_discount = remaining_part_to_consider * price_unit_after_discount

        if taxes:
            taxes_res = taxes.with_context(**base_line['extra_context']).compute_all(
                price_unit_after_discount,
                currency=currency,
                quantity=base_line['quantity'],
                product=base_line['product'],
                partner=base_line['partner'],
                is_refund=base_line['is_refund'],
                handle_price_include=base_line['handle_price_include'],
                include_caba_tags=include_caba_tags,
            )

            to_update_vals = {
                'tax_tag_ids': [Command.set(taxes_res['base_tags'])],
                'price_subtotal': taxes_res['total_excluded'],
                'price_total': taxes_res['total_included'],
            }

            if early_pay_discount_computation == 'excluded':
                new_taxes_res = taxes.with_context(**base_line['extra_context']).compute_all(
                    orig_price_unit_after_discount,
                    currency=currency,
                    quantity=base_line['quantity'],
                    product=base_line['product'],
                    partner=base_line['partner'],
                    is_refund=base_line['is_refund'],
                    handle_price_include=base_line['handle_price_include'],
                    include_caba_tags=include_caba_tags,
                )
                for tax_res, new_taxes_res in zip(taxes_res['taxes'], new_taxes_res['taxes']):
                    delta_tax = new_taxes_res['amount'] - tax_res['amount']
                    tax_res['amount'] += delta_tax
                    to_update_vals['price_total'] += delta_tax

            tax_values_list = []
            for tax_res in taxes_res['taxes']:
                tax_amount = tax_res['amount'] / rate
                if self.company_id.tax_calculation_rounding_method == 'round_per_line':
                    tax_amount = currency.round(tax_amount)
                tax_rep = self.env['account.tax.repartition.line'].browse(tax_res['tax_repartition_line_id'])
                tax_values_list.append({
                    **tax_res,
                    'tax_repartition_line': tax_rep,
                    'base_amount_currency': tax_res['base'],
                    'base_amount': currency.round(tax_res['base'] / rate),
                    'tax_amount_currency': tax_res['amount'],
                    'tax_amount': tax_amount,
                })

        else:
            price_subtotal = currency.round(price_unit_after_discount * base_line['quantity'])
            to_update_vals = {
                'tax_tag_ids': [Command.clear()],
                'price_subtotal': price_subtotal,
                'price_total': price_subtotal,
            }
            tax_values_list = []

        return to_update_vals, tax_values_list

class SaleOrderDiscount(models.TransientModel):
    _inherit = 'sale.order.discount'
    _description = "Discount Wizard"

    discount_type_new = fields.Selection(
        selection=[
            ('so_discount', "Global Discount"),
            ('amount', "Fixed Amount"),
        ],
        default='so_discount',
    )

    @api.constrains('discount_type_new', 'discount_percentage')
    def _check_discount_amount(self):
        for wizard in self:
            if (
                wizard.discount_type_new in ('sol_discount', 'so_discount')
                and wizard.discount_percentage > 1.0
            ):
                raise ValidationError(_("Invalid discount amount"))

    def action_apply_discount(self):
        self.ensure_one()
        self = self.with_company(self.company_id)
        if self.discount_type_new == 'sol_discount':
            self.sale_order_id.order_line.write({'discount': self.discount_percentage*100})
        else:
            self._create_discount_lines()

    def _create_discount_lines(self):
        """Create SOline(s) according to wizard configuration"""
        self.ensure_one()
        discount_product = self._get_discount_product()

        if self.discount_type_new == 'amount':
            vals_list = [
                self._prepare_discount_line_values(
                    product=discount_product,
                    amount=self.discount_amount,
                    taxes=self.env['account.tax'],
                )
            ]
        else: # so_discount
            total_price_per_tax_groups = defaultdict(float)
            for line in self.sale_order_id.order_line:
                if not line.product_uom_qty or not line.price_unit:
                    continue

                total_price_per_tax_groups[line.tax_id] += line.price_subtotal

            if not total_price_per_tax_groups:
                # No valid lines on which the discount can be applied
                return
            elif len(total_price_per_tax_groups) == 1:
                # No taxes, or all lines have the exact same taxes
                taxes = next(iter(total_price_per_tax_groups.keys()))
                subtotal = total_price_per_tax_groups[taxes]
                vals_list = [{
                    **self._prepare_discount_line_values(
                        product=discount_product,
                        amount=subtotal * self.discount_percentage,
                        taxes=taxes,
                        description=_(
                            "Discount: %(percent)s%%",
                            percent=self.discount_percentage*100
                        ),
                    ),
                }]
            else:
                vals_list = [
                    self._prepare_discount_line_values(
                        product=discount_product,
                        amount=subtotal * self.discount_percentage,
                        taxes=taxes,
                        description=_(
                            "Discount: %(percent)s%%"
                            "- On products with the following taxes %(taxes)s",
                            percent=self.discount_percentage*100,
                            taxes=", ".join(taxes.mapped('name'))
                        ),
                    ) for taxes, subtotal in total_price_per_tax_groups.items()
                ]
        return self.env['sale.order.line'].create(vals_list)


class ChooseDeliveryCarrier(models.TransientModel):
    _inherit = 'choose.delivery.carrier'
    _description = 'Delivery Carrier Selection Wizard'

    def button_confirm(self):
        if self.carrier_id:
            self.delivery_price = self.display_price
            self.carrier_id.fixed_price = self.display_price
            fixed_amount = self.carrier_id.fixed_price
            self.carrier_id.product_id.list_price = fixed_amount

        self.order_id.set_delivery_line(self.carrier_id, self.delivery_price)
        self.order_id.write({
            'recompute_delivery_price': False,
            'delivery_message': self.delivery_message,
        })


class ProjectTask(models.Model):
    _inherit = 'project.task'

    @api.model
    def create(self, vals):
        task = super(ProjectTask, self).create(vals)

        if task.sale_line_id and task.sale_line_id.order_id:
            project_tags = []
            for crm_tag in task.sale_line_id.order_id.tag_ids:
                matching_tag = self.env['project.tags'].search([('name', '=', crm_tag.name)], limit=1)
                if matching_tag:
                    project_tags.append(matching_tag.id)

            if project_tags:
                task.tag_ids = [(6, 0, project_tags)]

        return task

class ProjectProject(models.Model):
    _inherit = 'project.project'

    @api.model
    def create(self, vals):
        task = super(ProjectProject, self).create(vals)

        if task.sale_line_id and task.sale_line_id.order_id:
            project_tags = []
            for crm_tag in task.sale_line_id.order_id.tag_ids:
                matching_tag = self.env['project.tags'].search([('name', '=', crm_tag.name)], limit=1)
                if matching_tag:
                    project_tags.append(matching_tag.id)

            if project_tags:
                task.tag_ids = [(6, 0, project_tags)]

        return task