from odoo import models, fields, api,_
from odoo.exceptions import UserError
import base64

class AccountMove(models.Model):
    _inherit = 'account.move'

    brand_id = fields.Many2one(
        'brand.master', 
        string='Brand',
         domain="[('company_id', '=', company_id)]",
        help='Select the brand associated with this sale order'
    )

   
    terms_conditions = fields.Text(string='Brand Terms & Conditions')
    bom_id = fields.Many2one('bom.products', string='BOM', help='Select the Bill of Materials')
    payment_link = fields.Text(string='Payment Link')
    reference = fields.Char(string='Reference')
    discount_amount = fields.Monetary(
        string="Total Discount",
        compute="_compute_discount_amount",
        currency_field="currency_id"
    )
    sku_ids = fields.Many2many('product.template', string="SKU")
    formatted_invoice_date = fields.Char(
        string="Formatted Invoice Date",
        compute="_compute_formatted_dates",
    )

    formatted_due_date = fields.Char(
        string="Formatted Due Date",
        compute="_compute_formatted_dates",
    )

    tag_ids = fields.One2many(
        'crm.tag',  
        'invoice_id', 
        string='Tags',
        help='Select the brands associated with this company'
    )

    is_tag_access = fields.Boolean(compute="_compute_tag_access")
    has_tag_required = fields.Boolean(compute="_compute_has_tag_required", store=True)
    available_tag_ids = fields.Many2many(
        'crm.tag',
        compute="_compute_available_tags",
    )
    
    available_category_ids = fields.Many2many(
        'sku.type.master',
        compute="_compute_available_categories",
    )

    category_ids = fields.Many2many(
        'sku.type.master',
        'account_category_rel',
        'product_id',
        string='Categories',
        domain="[('brand_id', '=', brand_id),('id', 'in', available_category_ids)]",
        help='Select the Categories associated with the selected brand'
    )
    @api.depends("tag_ids")
    def _compute_available_tags(self):
        for record in self:
            record.available_tag_ids = self.env.user.tag_ids
            print(record.available_tag_ids,"ppppppppppppppppppppppppmubeenpssssssssssssssssssssssssss")
    @api.depends("category_ids")
    def _compute_available_categories(self):
        for record in self:
            record.available_category_ids = self.env.user.category_ids
            print(record.available_tag_ids,"ppppppppppppppppppppppppmubeenpssssssssssssssssssssssssss")



    @api.depends("brand_id", "brand_id.is_tag_show")
    def _compute_has_tag_required(self):
        for record in self:
            record.has_tag_required = bool(record.brand_id.is_tag_show)

    @api.depends("brand_id")
    def _compute_tag_access(self):
        for record in self:
            record.is_tag_access = record.brand_id.is_tag_show if record.brand_id else False


    def _compute_formatted_dates(self):
        for move in self:
            move.formatted_invoice_date = move.invoice_date.strftime("%d-%b-%Y") if move.invoice_date else ""
            move.formatted_due_date = move.invoice_date_due.strftime("%d-%b-%Y") if move.invoice_date_due else ""

    @api.onchange('invoice_date','invoice_date_due')
    def _compute_formatted_dates_onchange(self):
        for move in self:
            move.formatted_invoice_date = move.invoice_date.strftime("%d-%b-%Y") if move.invoice_date else ""
            move.formatted_due_date = move.invoice_date_due.strftime("%d-%b-%Y") if move.invoice_date_due else ""



    @api.depends("invoice_line_ids.price_subtotal", "invoice_line_ids.discount")
    def _compute_discount_amount(self):
        for move in self:
            total_discount = sum(
                (line.price_unit * line.quantity * line.discount / 100)
                for line in move.invoice_line_ids
            )
            move.discount_amount = total_discount
    
    @api.model
    def create(self, vals):
        user = self.env.user
        order = super(AccountMove, self).create(vals)
        if 'reference' in vals:
            order.message_post(
                body=f"Invoice with Reference: {order.reference}",
                message_type='notification',
                author_id=user.partner_id.id
            )
        return order

    def write(self, vals):
        user = self.env.user
        result = super(AccountMove, self).write(vals)
        for order in self:
            if 'reference' in vals:
                    order.message_post(
                        body=f"Invoice with Reference: {order.reference}",
                        message_type='notification',
                        author_id=user.partner_id.id
                    )
               
        return result

    @api.onchange('bom_id')
    def _onchange_bom_id(self):
        if self.bom_id:
            self.invoice_line_ids = [(5, 0, 0)]  
            new_lines = []
            for line in self.bom_id.line_product_ids:
                 new_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'quantity': line.product_uom_qty,
                    'name': line.product_id.name,
                    'price_unit': line.product_id.lst_price,
                }))
            
            self.invoice_line_ids = new_lines

    @api.onchange('brand_id')
    def _onchange_brand_id(self):
        if self.brand_id:
            self.category_ids = False
            self.invoice_line_ids  = [(6, 0, [])]
            self.terms_conditions = self.brand_id.terms_conditions_invoice

    def action_send_report_email(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Send Email',
            'res_model': 'invoice.order.email.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_invoice_order_id': self.id,
                'default_recipient_email': self.partner_id.email,
                'default_subject': f'Invoice {self.name}',
            },
        }


class InvoiceOrderEmailWizard(models.TransientModel):
    _name = 'invoice.order.email.wizard'
    _description = 'Invoice Order Email Wizard'

    invoice_order_id = fields.Many2one('account.move', string='Invoice', required=True, readonly=True)
    recipient_email = fields.Char(string='Recipient Email', required=True)
    subject = fields.Char(string='Subject', required=True, default='Purchase Order Report')

    def action_send_email(self):
        self.ensure_one()

        invoice = self.env['account.move'].browse(self.env.context.get('active_id'))
        if not invoice:
            raise UserError(_("No Invoice found to generate the email."))

        report_name = 'account.report_invoice'

        try:
            pdf_content, content_type = self.env['ir.actions.report']._render_qweb_pdf(
                report_name, [invoice.id]
            )

            pdf_base64 = base64.b64encode(pdf_content)
            attachment = self.env['ir.attachment'].create({
                'name': f"{invoice.name}.pdf",
                'type': 'binary',
                'datas': pdf_base64,
                'res_model': 'account.move',
                'res_id': invoice.id,
                'mimetype': 'application/pdf',
            })
            from_email = invoice.brand_id.inv_email
            if not from_email:
                raise UserError(_("No Invoice email is set for the selected brand."))
            mail_values = {
                'subject': self.subject or f"Purchase Order {invoice.name}",
                'body_html': _('Please find attached your Purchase Order.'),
                'email_from': from_email,
                'email_to': self.recipient_email,
                'attachment_ids': [(6, 0, [attachment.id])],
            }
            mail = self.env['mail.mail'].create(mail_values)
            mail.send()

        except Exception as e:
            raise UserError(_("An error occurred while generating the PDF: %s") % str(e))

        return {'type': 'ir.actions.act_window_close'}



class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    category_ids = fields.Many2many(
        'sku.type.master',
        'purchase_line_category_rel',
        'product_id',
        'category_id',
        string=' ',
        compute='_compute_product_sku_id',
        required=True,
        help='Select the Categories associated with the selected brand'
    )

    @api.depends('move_id.category_ids')
    def _compute_product_sku_id(self):
        """
        Compute the product template based on sku_ids from the order.
        This is just an example; this method may also involve other logic.
        """
        for line in self:
            for line in self:
                if not line.move_id.bom_id:
                    if line.move_id and line.move_id.category_ids:
                        line.category_ids = line.move_id.category_ids.ids
                    else:
                        line.category_ids = []
                else:
                    category_ids = self.env['sku.type.master'].search([]) 
                    line.category_ids = category_ids
            
    
            

    @api.onchange('product_id')
    def _compute_product_template_id(self):
        for line in self:
            if not line.move_id.bom_id:
                if line.move_id and line.move_id.category_ids:
                    self.category_ids = line.move_id.category_ids.ids
                else:
                    line.category_ids = []
            else:
                category_ids = self.env['sku.type.master'].search([]) 
                line.category_ids = category_ids
    
            
    