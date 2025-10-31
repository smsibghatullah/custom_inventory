

from odoo import models, fields, api, tools, Command, _
from odoo.exceptions import UserError,ValidationError
import re
import base64


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




    


