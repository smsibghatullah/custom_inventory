from odoo import models, fields, api
import base64
from datetime import datetime
import json
from markupsafe import Markup

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
        company = self.company_id or self.env.user.company_id
        task = False

        survey_names_list = []
        task_names_list = []
        project_names_list = []
        shift_assignment_links = []

        # ========= GENERATE PDF FOR EACH USER INPUT =========
        for user_input in user_inputs:

            if user_input.survey_id and user_input.survey_id.title:
                survey_names_list.append(user_input.survey_id.title)

            if user_input.task_id:
                task = task or user_input.task_id
                task_names_list.append(user_input.task_id.name or user_input.task_id.display_name)

            if user_input.project_id:
                project_names_list.append(user_input.project_id.name)
            elif user_input.task_id and user_input.task_id.project_id:
                project_names_list.append(user_input.task_id.project_id.name)

            if user_input.main_shift_assignment_id:
                assignment = user_input.main_shift_assignment_id
                assignment_name = assignment.display_name or assignment.name or str(assignment.id)

                shift_assignment_links.append(
                    '<a href="#" data-oe-model="%s" data-oe-id="%s">%s</a>' % (
                        assignment._name,
                        assignment.id,
                        assignment_name
                    )
                )

            pdf_content, _ = report_action._render_qweb_pdf(
                report_action.report_name,
                res_ids=[user_input.id]
            )

            attachment = self.env['ir.attachment'].sudo().create({
                'name': "%s - %s.pdf" % (user_input.survey_id.title or 'Survey', user_input.id),
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': 'survey.user_input',
                'res_id': user_input.id,
                'mimetype': 'application/pdf',
            })

            attachment_ids.append(attachment.id)

        survey_names = ', '.join(list(set(filter(None, survey_names_list)))) or 'Survey'
        task_names = ', '.join(list(set(filter(None, task_names_list)))) or ''
        project_names = ', '.join(list(set(filter(None, project_names_list)))) or ''
        shift_assignments = ', '.join(list(set(filter(None, shift_assignment_links)))) or ''

        company_name = company.name if company else self.env.user.company_id.name
        email_from = company.brand_email if company and company.brand_email else self.env.user.email_formatted

        template = self.env.ref(
            'custom_inventory.email_template_survey_result_report',
            raise_if_not_found=False
        )

        # ========= SEND EMAIL =========
        for partner in self.recipient_ids:
            if not partner.email:
                continue

            ctx = {
                'survey_names': survey_names,
                'task_names': task_names,
                'project_names': project_names,
                'total_reports': len(user_inputs),
                'company_name': company_name,
                'email_from': email_from,
                'partner_name': partner.name or 'User',
                'shift_assignments': shift_assignments,
            }

            if template:
                template_ctx = template.sudo().with_context(ctx)

                rendered_subject = template_ctx._render_field(
                    'subject',
                    [user_inputs[0].id],
                    compute_lang=True
                )

                rendered_body = template_ctx._render_field(
                    'body_html',
                    [user_inputs[0].id],
                    compute_lang=True
                )

                subject = rendered_subject.get(user_inputs[0].id) or "%s - Survey Report" % survey_names
                body_html = rendered_body.get(user_inputs[0].id) or ""
            else:
                subject = "%s - Survey Report" % survey_names
                body_html = """
                    <p>Dear %s,</p>
                    <p>Please find attached the survey report(s).</p>
                    <p>Regards,<br/>%s</p>
                """ % (partner.name or 'User', company_name)

            mail_values = {
                'subject': subject,
                'body_html': body_html,
                'email_to': partner.email,
                'email_cc': self.custom_email_cc or False,
                'email_from': email_from,
                'attachment_ids': [(6, 0, attachment_ids)],
            }

            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.sudo().send()

            # ========= TASK LOG / CHATTER =========
            if task:
                log_body = """
                <div style="font-family: Arial, sans-serif; font-size: 13px; color: #333;">
                    <p><b>Survey Email Sent</b></p>
                    <ul>
                        <li><b>To:</b> %s</li>
                        <li><b>CC:</b> %s</li>
                        <li><b>Subject:</b> %s</li>
                        <li><b>Survey:</b> %s</li>
                        <li><b>Project:</b> %s</li>
                        <li><b>Shift Assignment:</b> %s</li>
                        <li><b>Total Reports:</b> %s</li>
                    </ul>
                    <hr/>
                    %s
                </div>
                """ % (
                    partner.email or '',
                    self.custom_email_cc or '',
                    subject or '',
                    survey_names or '',
                    project_names or '',
                    shift_assignments or '',
                    len(user_inputs),
                    body_html or ''
                )

                task.sudo().message_post(
                    body=Markup(log_body),
                    subject=subject,
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                    attachment_ids=attachment_ids
                )

        return {'type': 'ir.actions.act_window_close'}