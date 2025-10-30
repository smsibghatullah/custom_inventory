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
        default=lambda self: self.env.company
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
    survey_input_id = fields.Many2one(
        'survey.user_input',
        string="Survey Answer",
        required=True
    )

    recipient_ids = fields.Many2many(
        'res.partner',
        string="Recipients",
        help="Select one or more recipients to send the survey report."
    )

    custom_email_cc = fields.Char(string="CC") 

    def action_generate_and_send_pdf(self):
        """Generate PDF, attach it, and send to selected partners."""
        self.ensure_one()
        answer = self.survey_input_id
        survey = answer.survey_id
        company = self.company_id

        company_logo = company.logo or False

        html = self.env['ir.qweb']._render('survey.survey_page_print', {
            'is_html_empty': False,
            'review': False,
            'survey': survey,
            'answer': answer,
            'questions_to_display': answer._get_print_questions(),
            'scoring_display_correction': survey.scoring_type in [
                'scoring_with_answers', 'scoring_with_answers_after_page'
            ] and answer,
            'format_datetime': lambda dt: self.env['ir.qweb.field.datetime'].value_to_html(dt, {}),
            'format_date': lambda date: self.env['ir.qweb.field.date'].value_to_html(date, {}),
            'graph_data': json.dumps(
                answer._prepare_statistics()[answer]
            ) if answer and survey.scoring_type in [
                'scoring_with_answers', 'scoring_with_answers_after_page'
            ] else False,
            'company_logo': company_logo,
            'company_name': company.name,
            'print_date': datetime.now().strftime('%d %b %Y, %I:%M %p'),
            'user': self.env.user
        })

        pdf_content = self.env['ir.actions.report']._run_wkhtmltopdf([html])

        attachment = self.env['ir.attachment'].sudo().create({
            'name': f"{survey.title or 'Survey'}.pdf",
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': 'survey.user_input',
            'res_id': answer.id,
            'mimetype': 'application/pdf',
        })
        self.attachment_id = attachment.id

        # === Send Email to all selected recipients ===
        for partner in self.recipient_ids:
            if not partner.email:
                continue  # skip if no email

            mail_values = {
                'subject': f"Survey Results: {survey.title}",
                'body_html': f"""
                    <p>Dear {partner.name or 'Valued User'},</p>
                    <p>Please find attached your survey result report.</p>
                    <p>Best regards,<br/>{company.name}</p>
                """,
                'email_to': partner.email,
                'email_cc': self.custom_email_cc or False,
                'email_from': self.brand_id.so_email,
                'attachment_ids': [(6, 0, [attachment.id])],
            }

            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.sudo().send()

        return {'type': 'ir.actions.act_window_close'}
