from odoo import models, fields, api
import base64
from datetime import datetime
import json

class SurveySendPDFWizard(models.TransientModel):
    _name = 'survey.send.pdf.wizard'
    _description = 'Send Survey PDF Wizard'

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        required=True,
    )

    brand_id = fields.Many2one(
        'brand.master',
        string='Brand',
        domain="[('company_ids', 'in', company_id)]",
        help='Select the brand associated with the selected company'
    )

    attachment_id = fields.Many2one(
        'ir.attachment',
        string="Attachment",
        help="Attach or review the generated PDF"
    )
    user_input_ids = fields.Many2many(
        'survey.user_input',
        string="Selected User Inputs"
    )

    recipient_ids = fields.Many2many(
        'res.partner',
        string="Recipients",
        help="Select one or more recipients to send the survey report."
    )

    custom_email_cc = fields.Char(string="CC") 

    def action_generate_and_send_pdf(self):
        self.ensure_one()

        user_inputs = self.user_input_ids
        if not user_inputs:
            return {'type': 'ir.actions.act_window_close'}

        report_action = self.env.ref(
            'custom_inventory.action_report_employment_certificate'
        )

        attachment_ids = []

        # ========= GENERATE PDF FOR EACH USER INPUT =========
        for user_input in user_inputs:

            pdf_content, _ = report_action._render_qweb_pdf(
                report_action.report_name,
                res_ids=[user_input.id]
            )

            attachment = self.env['ir.attachment'].sudo().create({
                'name': f"{user_input.survey_id.title or 'Survey'} - {user_input.id}.pdf",
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': 'survey.user_input',
                'res_id': user_input.id,
                'mimetype': 'application/pdf',
            })

            attachment_ids.append(attachment.id)

        # ========= SEND EMAIL =========
        company = self.company_id

        for partner in self.recipient_ids:
            if not partner.email:
                continue

            mail_values = {
                'subject': "Survey Report",
                'body_html': f"""
                    <p>Dear {partner.name or 'User'},</p>
                    <p>Please find attached the survey report(s).</p>
                    <p>Regards,<br/>{company.name}</p>
                """,
                'email_to': partner.email,
                'email_cc': self.custom_email_cc or False,
                'email_from': self.company_id.brand_email or self.env.user.email,
                'attachment_ids': [(6, 0, attachment_ids)],
            }

            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.sudo().send()

        return {'type': 'ir.actions.act_window_close'}
