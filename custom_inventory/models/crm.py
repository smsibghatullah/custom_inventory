

from odoo import models, fields, api,_, tools, Command
from odoo.exceptions import UserError,ValidationError
import re


class CrmLead(models.Model):
    _inherit = "crm.lead"


    brand_id = fields.Many2one(
        'brand.master',
        string='Brand',
         domain="[('company_id', '=', company_id)]",
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

    custom_email_to = fields.Char(string="Custom Email To")
    custom_email_from = fields.Char(string="Custom Email From")

    def action_send_mail(self):
        """ Used for action button that do not accept arguments. """
        print("ppp===========================mubeen================================>>>>>>>>>>>>>>>>>>")
        mail_server = self.env['ir.mail_server'].sudo().search([('smtp_user','=',self.custom_email_from)],limit=1)
        print(mail_server,"ppp===========================mubeen================================>>>>>>>>>>>>>>>>>>")
        self._action_send_mail(auto_commit=False)
        return {'type': 'ir.actions.act_window_close'}

    
    def _prepare_mail_values_rendered(self, res_ids):
        """Generate values that are already rendered. This is used mainly in
        monorecord mode, when the wizard contains value already generated
        (e.g. "Send by email" on a sale order, in form view).

        :param list res_ids: list of record IDs on which composer runs;

        :return dict results: for each res_id, the generated values used to
          populate in '_prepare_mail_values';
        """
        self.ensure_one()
        print("_prepare_mail_values_rendered","ppppppppppppppppppppp_prepare_mail_values_rendered")
        email_mode = self.composition_mode == 'mass_mail'

        # Duplicate attachments linked to the email.template. Indeed, composer
        # duplicates attachments in mass mode. But in 'rendered' mode attachments
        # may come from an email template (same IDs). They also have to be
        # duplicated to avoid changing their ownership.
        if self.composition_mode == 'comment' and self.template_id and self.attachment_ids:
            new_attachment_ids = []
            for attachment in self.attachment_ids:
                if attachment in self.template_id.attachment_ids:
                    new_attachment_ids.append(attachment.copy({
                        'res_model': 'mail.compose.message',
                        'res_id': self.id,
                    }).id)
                else:
                    new_attachment_ids.append(attachment.id)
            new_attachment_ids.reverse()
            self.write({'attachment_ids': [Command.set(new_attachment_ids)]})
            print(self.custom_email_from,"oooooooooooooooppppmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmpppppppppwwwwwwwwwwwww")
           

        return {
            res_id: {
                'attachment_ids': [attach.id for attach in self.attachment_ids],
                'body': self.body or '',
                'email_from': self.custom_email_from,
                # 'email_to': self.custom_email_to,
                'partner_ids': self.partner_ids.ids,
                'scheduled_date': self.scheduled_date,
                'subject': self.subject or '',
                **(
                    {
                        # notify parameter to force layout lang
                        'force_email_lang': self.lang,
                    } if not email_mode else {}
                ),
            }
            for res_id in res_ids
        }
        

    def _action_send_mail_comment(self, res_ids):
        """ Send in comment mode. It calls message_post on model, or the generic
        implementation of it if not available (as message_notify). """
        self.ensure_one()
        post_values_all = self._prepare_mail_values(res_ids)
        ActiveModel = self.env[self.model] if self.model and hasattr(self.env[self.model], 'message_post') else self.env['mail.thread']
        if self.composition_batch:
            # add context key to avoid subscribing the author
            ActiveModel = ActiveModel.with_context(
                mail_create_nosubscribe=True,
            )

        messages = self.env['mail.message']
        for res_id, post_values in post_values_all.items():
            if ActiveModel._name == 'mail.thread':
                post_values.pop('message_type')  # forced to user_notification
                post_values.pop('parent_id', False)  # not supported in notify
                if self.model:
                    post_values['model'] = self.model
                    post_values['res_id'] = res_id
                message = ActiveModel.message_notify(**post_values)
                if not message:
                    # if message_notify returns an empty record set, no recipients where found.
                    raise UserError(_("No recipient found."))
                messages += message
            else:
                messages += ActiveModel.browse(res_id).message_post(**post_values)
        print(messages,"oosmmmmmmmmmmjjjjjjjjjjjjjjjjj========================++><><><>>>>>>>>>>>>>>>>>>>")
        messages.mail_ids.write({
            'email_to': self.custom_email_to,
            'recipient_ids': [(5, 0, 0)],
        })
        return messages

    


