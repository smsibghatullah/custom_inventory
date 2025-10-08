from odoo import http
from odoo.http import request
import base64
import json
from datetime import datetime

from odoo.addons.survey.controllers.main import is_html_empty


class SurveyControllerExtended(http.Controller):

    @http.route('/survey/send_pdf/<int:answer_id>', type='http', auth='user', website=True)
    def send_survey_pdf_email(self, answer_id, **post):
        """
        Generate the survey result PDF with company logo and print date,
        send by email, and allow browser download.
        """
        answer_sudo = request.env['survey.user_input'].sudo().browse(answer_id)
        if not answer_sudo.exists():
            return "Survey answer not found."

        survey_sudo = answer_sudo.survey_id
        company = request.env.company
        print(company.logo,"=======================")

        # Get company logo
        company_logo = False
        if company.logo:
            company_logo = company.logo

        # Render HTML with additional context
        html = request.env['ir.qweb']._render('survey.survey_page_print', {
            'is_html_empty': is_html_empty,
            'review': False,
            'survey': survey_sudo,
            'answer': answer_sudo,
            'questions_to_display': answer_sudo._get_print_questions(),
            'scoring_display_correction': survey_sudo.scoring_type in [
                'scoring_with_answers', 'scoring_with_answers_after_page'
            ] and answer_sudo,
            'format_datetime': lambda dt: request.env['ir.qweb.field.datetime'].value_to_html(dt, {}),
            'format_date': lambda date: request.env['ir.qweb.field.date'].value_to_html(date, {}),
            'graph_data': json.dumps(
                answer_sudo._prepare_statistics()[answer_sudo]
            ) if answer_sudo and survey_sudo.scoring_type in [
                'scoring_with_answers', 'scoring_with_answers_after_page'
            ] else False,
            'company_logo': company_logo,
            'company_name': company.name,
            'print_date': datetime.now().strftime('%d %b %Y, %I:%M %p'),
        })

        # Convert HTML to PDF
        pdf_content = request.env['ir.actions.report']._run_wkhtmltopdf([html])

        # Create attachment
        attachment = request.env['ir.attachment'].sudo().create({
            'name': f"{survey_sudo.title or 'Survey'}.pdf",
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': 'survey.user_input',
            'res_id': answer_sudo.id,
            'mimetype': 'application/pdf',
        })

        # Send email
        recipient_email = answer_sudo.partner_id.email or 'm.mubeen1020@gmail.com'
        mail_values = {
            'subject': f"Survey Results: {survey_sudo.title}",
            'body_html': f"""
                <p>Dear {answer_sudo.partner_id.name or 'User'},</p>
                <p>Please find attached your survey result report.</p>
            """,
            'email_to': recipient_email,
            'email_from': request.env.company.email or 'accounts@ezylock.co.nz',
            'attachment_ids': [(6, 0, [attachment.id])],
        }

        mail = request.env['mail.mail'].sudo().create(mail_values)
        mail.sudo().send()

        # Return PDF for download
        filename = f"{survey_sudo.title or 'Survey'}.pdf"
        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', f'attachment; filename="{filename}"'),
        ]
        return request.make_response(pdf_content, headers=headers)
