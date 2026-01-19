

from ..utils import crm_leads 
from odoo import models, fields, api, tools, Command, _
from odoo.exceptions import UserError,ValidationError
import re
import base64

import logging
_logger = logging.getLogger(__name__)

class CrmLead(models.Model):
    _inherit = "crm.lead"


    brand_id = fields.Many2one(
        'brand.master',
        string='Brand',
         domain="[('company_ids', 'in', company_id)]",
        help='Select the brand associated with this sale order'
    )

    category_id = fields.Many2one(
        'sku.type.master',
        string='Category',
        domain="[('brand_id', '=', brand_id), ('id', 'in', available_sku_category_ids)]",
        help='Select the Category associated with the selected brand'
    )

    category_ids = fields.Many2many(
        'sku.type.master',
        'crm_category_rel',
        'product_id',
        'category_id',
        string='Categories *',
         required=True,
        help='Select the Categories associated with the selected brand'
    )

    record_count = fields.Integer(string="Record Count", default=1)

    sku_ids = fields.Many2many('product.template', string="SKU")

    available_tag_ids = fields.Many2many(
        'crm.tag',
        compute="_compute_available_tags",
    )
    available_sku_category_ids = fields.Many2many(
        'sku.type.master',
        compute="_compute_available_categories",
    )
    bci_project = fields.Char(string='BCI Project', required=True)
    mobile_no = fields.Char(string='Mobile')
    is_tag_access = fields.Boolean(compute="_compute_tag_access")
    has_tag_required = fields.Boolean(compute="_compute_has_tag_required", store=True)

    invoice_total_amount = fields.Monetary(compute='_compute_invoice_payment_data', string="Invoices", currency_field='company_currency')
    total_payment = fields.Monetary(compute='_compute_invoice_payment_data', string="Payments", currency_field='company_currency')
    invoice_count = fields.Integer(compute='_compute_invoice_payment_data', string="Number of Invoices")
    payment_count = fields.Integer(compute='_compute_invoice_payment_data', string="Number of Register Payments")

    total_cost_amount = fields.Monetary(compute='_compute_cost_data', string="Total Cost", currency_field='company_currency')
    cost_count = fields.Integer(compute='_compute_cost_data', string="Number of Timesheets")

    additional_salesperson_ids = fields.Many2many(
        'res.users',
        string='Additional Salespersons',
        help="Select multiple salespersons who can also view thie crm lead"
    )

    @api.model
    def create(self, vals):
        if vals.get('expected_revenue', 0) <= 0:
            raise ValidationError(_("Expected Revenue must be greater than zero."))
        
        return super(CrmLead, self).create(vals)


    @api.depends("brand_id", "brand_id.is_tag_show")
    def _compute_has_tag_required(self):
        for record in self:
            record.has_tag_required = bool(record.brand_id.is_tag_show)

    @api.depends("brand_id")
    def _compute_tag_access(self):
        for record in self:
            record.is_tag_access = record.brand_id.is_tag_show if record.brand_id else False

    @api.constrains('mobile_no')
    def _check_mobile_no(self):
        for record in self:
            if record.mobile_no and not re.match(r'^\+?\d{7,15}$', record.mobile_no):
                raise models.ValidationError("Enter a valid mobile number (7-15 digits, optional + at start).")

    @api.depends("tag_ids")
    def _compute_available_tags(self):
        for record in self:
            record.available_tag_ids = self.env.user.tag_ids
            print(record.available_tag_ids,"ppppppppppppppppppppppppmubeenpssssssssssssssssssssssssss")
    @api.depends("category_id")
    def _compute_available_categories(self):
        for record in self:
            record.available_sku_category_ids = self.env.user.sku_category_ids
            print(record.available_tag_ids,"ppppppppppppppppppppppppmubeenpssssssssssssssssssssssssss")

    
    @api.depends('order_ids.state', 'order_ids.invoice_ids.payment_state', 'order_ids.invoice_ids.amount_total')
    def _compute_invoice_payment_data(self):
        for lead in self:
            total_invoiced = 0.0
            total_paid = 0.0
            company_currency = lead.company_currency or self.env.company.currency_id
            
            invoices = lead.order_ids.mapped('invoice_ids').filtered(lambda inv: inv.move_type == 'out_invoice' and inv.state != 'cancel')

            for invoice in invoices:
                total_invoiced += invoice.currency_id._convert(
                    invoice.amount_total, company_currency, invoice.company_id, invoice.invoice_date or fields.Date.today()
                )
                
                amount_paid = invoice.amount_total - invoice.amount_residual
                total_paid += invoice.currency_id._convert(
                    amount_paid, company_currency, invoice.company_id, invoice.invoice_date or fields.Date.today()
                )
                
            lead.invoice_total_amount = total_invoiced
            lead.total_payment = total_paid

            lead.invoice_count = len(invoices)
            lead.payment_count = len(invoices)

    @api.depends('order_ids.project_id.task_ids.timesheet_ids.amount')
    def _compute_cost_data(self):
        for lead in self:
            total_cost = 0.0
            company_currency = lead.company_currency or self.env.company.currency_id
            
            timesheets = lead.order_ids.mapped('project_id.task_ids.timesheet_ids').filtered(lambda t: t.unit_amount != 0)
            for sheet in timesheets:
                if sheet.currency_id and sheet.currency_id != company_currency:
                     total_cost += sheet.currency_id._convert(
                        sheet.unit_amount, company_currency, sheet.company_id, sheet.date or fields.Date.today()
                    )
                else:
                    total_cost += sheet.unit_amount

            lead.total_cost_amount = total_cost
            lead.cost_count = len(timesheets)


    def action_view_invoices(self):
        invoices = self.order_ids.mapped('invoice_ids').filtered(lambda inv: inv.move_type == 'out_invoice')
        action = self.env['ir.actions.actions']._for_xml_id('account.action_move_out_invoice_type')
        action['domain'] = [('id', 'in', invoices.ids)]
        return action

    def action_view_payments(self):
        invoices = self.order_ids.mapped('invoice_ids').filtered(lambda inv: inv.move_type == 'out_invoice' and inv.payment_state in ('paid', 'in_payment'))
        payment_ids = []
        for invoice in invoices:
            for move_line in invoice.line_ids:
                if move_line.account_type in ('asset_receivable', 'liability_payable'):
                    payment_lines = move_line.matched_debit_ids.mapped('debit_move_id') + move_line.matched_credit_ids.mapped('credit_move_id')
                    payment_ids.extend(payment_lines.mapped('payment_id').ids)


        action = self.env['ir.actions.actions']._for_xml_id('account.action_account_payments')
        
        action['domain'] = [('id', 'in', payment_ids)]
        return action
    
    def action_view_costs(self):
        return False
    
    def _prepare_opportunity_quotation_context(self):
        """ Prepares the context for a new quotation (sale.order) by sharing the values of common fields """
        self.ensure_one()
        context = super(CrmLead, self)._prepare_opportunity_quotation_context()

        context.update({
            'default_brand_id': self.brand_id.id,
            'default_category_ids': [(6, 0, [self.category_id.id])],
            'default_bci_project': self.bci_project,
            'default_reference': self.name,
        })
        print(context)

        return context



class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    custom_email_to = fields.Many2many(
        'res.partner',
        'res_partner_email_rel_we',
        string="Custom Email To"
    )
    custom_email_from = fields.Char(string="Custom Email From")
    custom_email_cc = fields.Char(string="CC") 
    sale_order_id = fields.Many2one('sale.order', string="Sale Order")
    purchase_order_id = fields.Many2one('purchase.order', string="Purchase Order")
      

    def action_send_mail(self):
        """Send email with Sale/Purchase attachments"""
        for wizard in self:
            email_to_list = wizard.custom_email_to.mapped('email')
            email_to = ', '.join(filter(None, email_to_list))

            if not email_to:
                raise UserError(_("Please select at least one recipient (Custom Email To)."))

            if not wizard.custom_email_from:
                raise UserError(_("Please enter Custom Email From address."))

            print(wizard.custom_email_from,"======================================wizard.custom_email_from")   

            mail_values = {
                'email_from': wizard.custom_email_from,
                'email_to': email_to,
                'email_cc': wizard.custom_email_cc or False,
                'subject': wizard.subject or "No Subject",
                'body_html': wizard.body or "",
                'state': 'outgoing',
                'auto_delete': False,
            }

            mail = self.env['mail.mail'].sudo().create(mail_values)
            attachment_ids = []


            mail.write({'attachment_ids': [(6, 0, self.attachment_ids.ids)]})

            mail.sudo().send()
            mail.sudo().write({'state': 'sent'})

            res_ids = wizard._evaluate_res_ids()
            self._action_send_mail_comment(res_ids)

        return {'type': 'ir.actions.act_window_close'}


    def _action_send_mail_comment(self, res_ids):
        """ Send in comment mode. It calls message_post on model, or the generic
        implementation of it if not available (as message_notify). """
        self.ensure_one()
        post_values_all = self._prepare_mail_values(res_ids)
        ActiveModel = self.env[self.model] if self.model and hasattr(self.env[self.model], 'message_post') else self.env['mail.thread']
        if self.composition_batch:
            ActiveModel = ActiveModel.with_context(
                mail_create_nosubscribe=True,
            )

        messages = self.env['mail.message']
        email_list = self.custom_email_to.mapped('email')
        email_string = ','.join(filter(None, email_list)) 
        print(email_string,"=================>>>>>>>>>><<<<<<<<<<<<<<<<============================11111112222222233333333333")

        for res_id, post_values in post_values_all.items():
            if ActiveModel._name == 'mail.thread':
                post_values.pop('message_type')
                post_values.pop('parent_id', False) 
                if self.model:
                    post_values['model'] = self.model
                    post_values['res_id'] = res_id
                message = ActiveModel.message_notify(**post_values)
                if not message:
                    raise UserError(_("No recipient found."))
                messages += message
            else:
                messages += ActiveModel.browse(res_id).message_post(**post_values)
        print(messages,"oosmmmmmmmmmmjjjjjjjjjjjjjjjjj========================++><><><>>>>>>>>>>>>>>>>>>>")
        email_list = self.custom_email_to.mapped('email')
        email_string = ', '.join(filter(None, email_list))

        if self.purchase_order_id:
            if email_string:
                self.purchase_order_id.message_post(
                    body=f"To Emails: {email_string}",
                    message_type="comment",
                    subtype_xmlid="mail.mt_note"
                )
            if self.custom_email_cc:
                self.purchase_order_id.message_post(
                    body=f"CC Email: {self.custom_email_cc}",
                    message_type="comment",
                    subtype_xmlid="mail.mt_note"
                )
            if self.custom_email_from:
                self.purchase_order_id.message_post(
                    body=f"From Email: {self.custom_email_from}",
                    message_type="comment",
                    subtype_xmlid="mail.mt_note"
                )

        if self.sale_order_id:
            if email_string:
                self.sale_order_id.message_post(
                    body=f"To Emails: {email_string}",
                    message_type="comment",
                    subtype_xmlid="mail.mt_note"
                )
            if self.custom_email_cc:
                self.sale_order_id.message_post(
                    body=f"CC Email: {self.custom_email_cc}",
                    message_type="comment",
                    subtype_xmlid="mail.mt_note"
                )
            if self.custom_email_from:
                self.sale_order_id.message_post(
                    body=f"From Email: {self.custom_email_from}",
                    message_type="comment",
                    subtype_xmlid="mail.mt_note"
                )

        return messages


class SaleOrderLead(models.Model):
    _inherit = 'sale.order'

    amount_invoiced_so = fields.Monetary(compute='_compute_amounts_so', string="Invoiced Amount", currency_field='currency_id')
    amount_paid_so = fields.Monetary(compute='_compute_amounts_so', string="Paid Amount", currency_field='currency_id')
    amount_cost_so = fields.Monetary(compute='_compute_cost_so', string="Total Cost", currency_field='currency_id')
    profitability_amount_cost_so = fields.Monetary(compute='_compute_cost_so', string="Total Cost", currency_field='currency_id')
    other_profitability_cost_so = fields.Monetary(
        string="Other Cost", 
        currency_field='currency_id', 
        help="Manual entry for other costs not covered by timesheets."
    )
    
    #Deprecated: need to be removed
    lead_id = fields.Many2one(
        'crm.lead', 
        string='Related Lead', 
        domain="[('company_id', '=', company_id)]",
        help="Link this sales order to a specific lead from the same company."
    )    

    total_profitability_so = fields.Monetary(
        string='Profitability',
        compute='_compute_profitability_so',
        currency_field='currency_id',
        store=True,
    )

    profitability_percentage_so = fields.Float(
        string='Profit %',
        compute='_compute_profitability_percentage_so',
        digits=(12, 2),
        store=True,
    )


    def action_view_full_so(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sales Order',
            'res_model': 'sale.order',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',  # 'current' target means full page, not popup
        }

    @api.depends('amount_total', 'profitability_amount_cost_so', 'other_profitability_cost_so')
    def _compute_profitability_so(self):
        for order in self:
            revenue = order.amount_total or 0.0
            cost = order.profitability_amount_cost_so or 0.0
            other_cost = order.other_profitability_cost_so or 0.0
            order.total_profitability_so = revenue - cost - other_cost
    
    @api.depends('amount_total', 'profitability_amount_cost_so', 'other_profitability_cost_so', 'total_profitability_so')
    def _compute_profitability_percentage_so(self):
        for order in self:
            revenue = order.amount_total or 0.0
            profitability = order.total_profitability_so or 0.0
            if revenue:
                order.profitability_percentage_so = (profitability / revenue) * 100
            else:
                order.profitability_percentage_so = 0.0
    
    @api.depends('invoice_ids.payment_state', 'invoice_ids.amount_total', 'invoice_ids.amount_residual')
    def _compute_amounts_so(self):
        for order in self:
            total_invoiced = 0.0
            total_paid = 0.0
            currency = order.currency_id or self.env.company.currency_id

            invoices = order.invoice_ids.filtered(lambda inv: inv.move_type == 'out_invoice' and inv.state != 'cancel')

            for invoice in invoices:
                total_invoiced += invoice.currency_id._convert(
                    invoice.amount_total, currency, order.company_id, invoice.invoice_date or fields.Date.today()
                )
                amount_paid = invoice.amount_total - invoice.amount_residual
                total_paid += invoice.currency_id._convert(
                    amount_paid, currency, order.company_id, invoice.invoice_date or fields.Date.today()
                )
            
            order.amount_invoiced_so = total_invoiced
            order.amount_paid_so = total_paid

    @api.depends(
            'project_id.task_ids.timesheet_ids.amount',
            'order_line.product_id.standard_price',
        )
    def _compute_cost_so(self):
        for order in self:
            total_cost = 0.0
            currency = order.currency_id or self.env.company.currency_id

            timesheets = order.project_id.task_ids.timesheet_ids.filtered(lambda t: t.unit_amount != 0)
            total_product_cost = 0.0
            for line in order.order_line:
                cost = line.product_id.standard_price
                total_product_cost += cost * line.product_uom_qty

            current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
            for sheet in timesheets:
                if sheet.currency_id and sheet.currency_id != currency:
                     total_cost += sheet.currency_id._convert(
                        sheet.unit_amount, currency, order.company_id, sheet.date or fields.Date.today()
                    )
                else:
                    total_cost += sheet.unit_amount
                
                total_cost = total_cost * current_employee.hourly_cost

            order.profitability_amount_cost_so = total_cost + total_product_cost
            order.amount_cost_so = order.profitability_amount_cost_so + order.other_profitability_cost_so

    @api.model
    def create(self, vals):
        record = super(SaleOrderLead, self).create(vals)

        for order in record:
            if order.opportunity_id and order.state == 'draft':
                subject = f"Sale Order {order.name}"
                body = _("Sale Order: <a href='#id=%(so_id)s&model=sale.order'>%(so_name)s</a> created with state: <b>%(state)s</b>.") % {'so_id': order.id, 'so_name': order.name, 'state': dict(order._fields['state'].selection).get(order.state)}
                crm_leads.log_to_crm_history(subject, body, order)
        return record
    
    def write(self, vals):
        result = super(SaleOrderLead, self).write(vals)

        
        for order in self:
            if order.opportunity_id:
                if 'state' in vals:
                    subject = f"Sale Order Status Update: {order.name}"
                    body = _("Sale Order: <a href='#id=%(so_id)s&model=sale.order'>%(so_name)s</a> state changed to: <b>%(state)s</b>.") % {'so_id': order.id, 'so_name': order.name, 'state': dict(order._fields['state'].selection).get(order.state)}
                    crm_leads.log_to_crm_history(subject, body, order)

                if 'project_id' in vals:
                    if order.project_id:
                        subject = f"Project Linked to SO: {order.name}"
                        body = _("Project <a href='#id=%(project_id)s&model=project.project'>%(project_name)s</a> was linked to this Sale Order %(so_name)s") % {'project_id': order.project_id.id, 'project_name': order.project_id.name, 'so_name': order.name}
                        crm_leads.log_to_crm_history(subject, body, order)

                if 'opportunity_id' in vals:
                    subject = f"CRM Lead Linked to SO: {order.name}"
                    body = _(f"This Sale Order {order.name} was linked to the CRM Lead.")
                    crm_leads.log_to_crm_history(subject, body, order)

        return result
    

class ProjectTaskLead(models.Model):
    _inherit = 'project.task'

    def write(self, vals):
        result = super(ProjectTaskLead, self).write(vals)
        _logger.info(f"555555 {vals}")
        _logger.info(f"444444444 {self.project_id}")
        sale_order = self.env['sale.order'].search([('project_id', '=', self.project_id.id)], limit=1)
        _logger.info(f"66666666666 {sale_order}")
        if self.project_id and sale_order:
            if 'name' in vals:
                subject = f"Task {self.name}"
                # sale_order = self.project_id.sale_order_id
                body = _(
                    "A task <a href='#id=%(task_id)s&model=project.task'>%(task_name)s</a> is linked with project %(project_name)s for SO: %(so_ref)s."
                ) % {
                    'task_id': self.id,
                    'task_name': self.name,
                    'project_name': self.project_id.name,
                    'so_ref': sale_order.name
                }

            # Call your helper function, passing the Sale Order object
                crm_leads.log_to_crm_history(subject, body, sale_order)
            
            if 'state' in vals:
                subject = f"Task {self.name}"
                body = _(
                    "A status %(task_status)s of a task <a href='#id=%(task_id)s&model=project.task'>%(task_name)s</a> is updated with project %(project_name)s for SO: %(so_ref)s."
                ) % {
                    'task_status': self.state,
                    'task_id': self.id,
                    'task_name': self.name,
                    'project_name': self.project_id.name,
                    'so_ref': sale_order.name
                }

            # Call your helper function, passing the Sale Order object
                crm_leads.log_to_crm_history(subject, body, sale_order)


    # @api.model
    # def create(self, vals):
    #     record = super(ProjectTaskLead, self).create(vals)

    #     if record.project_id and record.project_id.sale_order_id:
    #         subject = f"Task Created: {record.name}"
    #         body = _("A new task <a href='#id=%(task_id)s&model=project.task'>%(task_name)s</a> was created for SO: %(so_ref)s.") % {'task_id': record.id, 'task_name': record.name, 'so_ref': record.project_id.sale_order_id.name}
            
    #         crm_leads.log_to_crm_history(subject, body, record)

    #     return record
    

class AccountPaymentRegisterInherit(models.TransientModel):
    _inherit = ['account.payment.register']

    def action_create_payments(self):

        invoices = self.mapped('line_ids.move_id')
        
        result = super(AccountPaymentRegisterInherit, self).action_create_payments()

        for invoice in invoices:
            if invoice.invoice_origin:
                sale_order = self.env['sale.order'].search([('name', '=', invoice.invoice_origin)], limit=1)
                
                if sale_order and sale_order.opportunity_id:
                    subject = f"Payment Registered for Invoice: {invoice.name}"
                    
                    body = _("Payment Done to invoice <a href='#id=%(inv_id)s&model=account.move'>%(inv_name)s</a> linked to SO: %(so_ref)s.") % {
                        'inv_id': invoice.id,
                        'inv_name': invoice.name,
                        'so_ref': sale_order.name
                    }
                    
                    crm_leads.log_to_crm_history(subject, body, sale_order)

        return result