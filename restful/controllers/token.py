import json
import logging

import werkzeug.wrappers
from odoo import http, models, fields
from odoo import http
from odoo.addons.restful.common import invalid_response, valid_response
from odoo.exceptions import AccessDenied, AccessError
from odoo.http import request
import base64
from odoo.service import db
from datetime import date
from datetime import datetime

_logger = logging.getLogger(__name__)


class AccessToken(http.Controller):
    """."""

    def __init__(self):

        self._token = request.env["api.access_token"]
        
    @http.route('/api/send_survey_via_email', type='json', auth='user', methods=['POST'], csrf=False)
    def send_survey_via_email(self, **kwargs):
        # Decode & parse JSON
        payload_str = request.httprequest.data.decode()
        print(payload_str, "=========================")

        try:
            payload = json.loads(payload_str or "{}")
        except Exception as e:
            return {"success": False, "error": f"Invalid JSON: {str(e)}"}

        user_input_ids = payload.get("user_input_ids", [])
        user_id = payload.get("user_id")
        recipient_ids = payload.get('recipients', [])
        cc_emails = payload.get('cc', []) or payload.get('ccEmail', [])

        if not user_input_ids:
            return {"success": False, "error": "No survey inputs provided"}

        attachments = []

        for u_input_id in user_input_ids:
            answer = request.env['survey.user_input'].sudo().browse(u_input_id)
            if not answer.exists():
                continue

            survey = answer.survey_id

            # Determine company
            company = None
            if user_id:
                user = request.env['res.users'].sudo().browse(int(user_id))
                if user.exists():
                    company = user.company_id
            if not company:
                company = answer.company_id or request.env.user.company_id

            company_logo = company.logo or False

            # Render HTML
            html = request.env['ir.qweb']._render('survey.survey_page_print', {
                'is_html_empty': False,
                'review': False,
                'survey': survey,
                'answer': answer,
                'questions_to_display': answer._get_print_questions(),
                'scoring_display_correction': survey.scoring_type in [
                    'scoring_with_answers', 'scoring_with_answers_after_page'
                ] and answer,
                'format_datetime': lambda dt: request.env['ir.qweb.field.datetime'].value_to_html(dt, {}),
                'format_date': lambda date: request.env['ir.qweb.field.date'].value_to_html(date, {}),
                'graph_data': json.dumps(answer._prepare_statistics()[answer]) if answer and survey.scoring_type in [
                    'scoring_with_answers', 'scoring_with_answers_after_page'
                ] else False,
                'company_logo': company_logo,
                'company_name': company.name,
                'print_date': datetime.now().strftime('%d %b %Y, %I:%M %p'),
                'user': request.env.user
            })

            pdf_content = request.env['ir.actions.report']._run_wkhtmltopdf([html])
            attachment = request.env['ir.attachment'].sudo().create({
                'name': f"{survey.title or 'Survey'}_{answer.id}.pdf",
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': 'survey.user_input',
                'res_id': answer.id,
                'mimetype': 'application/pdf',
            })
            attachments.append(attachment.id)

        if not attachments:
            return {"success": False, "error": "No valid survey PDFs generated"}

        mail_values = {
            'subject': f"Survey Results",
            'body_html': f"""
                <p>Dear User,</p>
                <p>Please find attached your survey result reports.</p>
                <p>Best regards,<br/>{company.name}</p>
            """,
            'email_to': ','.join(recipient_ids) if isinstance(recipient_ids, list) else recipient_ids,
            'email_cc': ','.join(cc_emails) if cc_emails else False,
            'email_from': company.brand_email or request.env.user.email_formatted,
            'attachment_ids': [(6, 0, attachments)],
        }

        mail = request.env['mail.mail'].sudo().create(mail_values)
        mail.send()

        return {"success": True, "message": "Survey PDFs sent successfully"}


    @http.route('/api/survey/update_input/<int:record_id>', type='json', auth='user', methods=['POST'], csrf=False)
    def update_survey_input(self, record_id, **kwargs):
        try:
            today = date.today()
            payload = request.httprequest.data.decode()
            payload = json.loads(payload or "{}")
            if not payload:
                return {"error": "No data provided"}

            project_id = payload.get("project_id")
            task_id = payload.get("task_id")

            survey_input = False

            if project_id:
                survey_input = request.env['survey.user_input'].sudo().search([
                    ("deadline", "=", today),
                    ("state", "in", ["in_progress", "done"]),
                    ("survey_id", "=", record_id),
                    ("project_id", "=", project_id),
                ], limit=1, order="id desc")

            elif task_id:
                survey_input = request.env['survey.user_input'].sudo().search([
                    ("deadline", "=", today),
                    ("state", "in", ["in_progress", "done"]),
                    ("survey_id", "=", record_id),
                    ("task_id", "=", task_id),
                ], limit=1, order="id desc")

            print(survey_input, "======================================survey input")
            if not survey_input.exists():
                return {"error": "Survey input not found"}

            line_ids = payload.pop("user_input_line_ids", [])
            print(line_ids, "================ line_ids raw")

            survey_input.sudo().user_input_line_ids.unlink()

            new_line_ids = []
            for line in line_ids:
                if isinstance(line, (list, tuple)) and len(line) >= 3 and isinstance(line[2], dict):
                    vals = line[2]
                elif isinstance(line, dict):
                    vals = line
                else:
                    continue

                vals.pop("id", None)
                vals["user_input_id"] = survey_input.id

                print(vals, "================ cleaned vals")
                new_line = request.env["survey.user_input.line"].sudo().create(vals)
                print(new_line, "================ created line")
                new_line_ids.append(new_line.id)

            if payload:
                survey_input.sudo().write(payload)

            return {
                "success": True,
                "message": "Survey input updated successfully",
                "id": survey_input.id,
                "new_line_ids": new_line_ids,
            }

        except Exception as e:
            return {"error": str(e)}




    @http.route('/equipment/public/<int:record_id>/private', type="http", auth="public", methods=["GET"], csrf=False)
    def get_equipment_info(self, record_id, **kwargs):
        try:
            equipment = request.env['maintenance.equipment'].sudo().browse(record_id)
            print(equipment.maintenance_team_id, "mmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmm", 
                equipment.technician_user_id, equipment.rating_ids)

            if not equipment.exists():
                return {"error": "Equipment not found"}

            private_fields = request.env['maintenance.equipment.access'].sudo().search([
                ('equipment_id', '=', record_id),
                ('is_private', '=', True)
            ]).mapped('field_name')

            private_data = {}
            for field in private_fields:
                if hasattr(equipment, field):
                    value = getattr(equipment, field)
                    field_label = equipment._fields[field].string if field in equipment._fields else field
                    if isinstance(value, models.Model):  
                        field_value = value.mapped('display_name') if len(value) > 1 else (value.display_name if value else None)
                    else:
                        field_value = value
                    private_data[field_label] = field_value


            public_fields = request.env['maintenance.equipment.access'].sudo().search([
                ('equipment_id', '=', record_id),
                ('is_public', '=', True)
            ]).mapped('field_name')

            public_data = {}
            for field in public_fields:
                if hasattr(equipment, field):
                    value = getattr(equipment, field)
                    if isinstance(value, models.Model):  
                        public_data[field] = value.mapped('display_name') if len(value) > 1 else (value.display_name if value else None)
                    else:
                        public_data[field] = value


            response_data = {
                "id": equipment.id,
                "name": equipment.name,
                "private_fields": private_data,
                "public_fields" : public_data
            }
            return valid_response(response_data)

        except Exception as e:
            return {"error": "Unexpected error", "message": str(e)}

    @http.route(['/equipment/public/<int:equipment_id>'], type='http', auth='public', website=True)
    def public_equipment_page(self, equipment_id, **kw):
        equipment = request.env['maintenance.equipment'].sudo().browse(equipment_id)
        if not equipment.exists():
            return request.not_found()

        public_fields = request.env['maintenance.equipment.access'].sudo().search([
                ('equipment_id', '=', equipment_id),
                ('is_public', '=', True)
            ]).mapped('field_name')

        public_data = []
        for field in public_fields:
            if hasattr(equipment, field):
                value = getattr(equipment, field)
                field_label = equipment._fields[field].string if field in equipment._fields else field
                if isinstance(value, models.Model):
                    value = value.mapped('display_name') if len(value) > 1 else (value.display_name if value else None)
                public_data.append({
                    'label': field_label,  
                    'value': value if value else 'N/A'
                })

        return request.render('custom_inventory.template_equipment_public_view', {
            'data': public_data
        })


    @http.route('/api/survey_question_data/<int:survey_id>', type="http", auth="public", methods=["GET"], csrf=False)
    def get_survey_questions(self, survey_id, **kwargs):
        try:
            survey = request.env['survey.survey'].sudo().browse(survey_id)
            if not survey.exists():
                return {"error": "Survey not found"}

            questions_data = []
            questions = request.env['survey.question'].sudo().search([('id', 'in', survey.question_ids.ids)])
            for question in questions:
                answer_ids = question.suggested_answer_ids.ids + question.matrix_row_ids.ids
                answers = request.env['survey.question.answer'].sudo().search([('id', 'in', answer_ids)])
                answers_data = [
                    {
                        "answer_id": answer.id,
                        "answer_value": answer.value,
                        "answer_type": answer.question_type,
                    }
                    for answer in answers
                ]
                questions_data.append({
                    "question_id": question.id,
                    "question_name": question.display_name,
                    "question_type": question.question_type,
                    "answers": answers_data
                })
            response_data = {
                "survey_id": survey.id,
                "survey_title": survey.title,
                "questions": questions_data
            }
            return valid_response(response_data)

        except AccessError as e:
            return {"error": "Access error", "message": str(e)}

        except Exception as e:
            return {"error": "Unexpected error", "message": str(e)}

    @http.route('/api/list_databases', type="http", auth="public", methods=["GET"], csrf=False)
    def list_databases(self, **kwargs):
        try:
            databases = db.list_dbs()  
            db_data = [{"id": index + 1, "name": name} for index, name in enumerate(databases)]
            return valid_response(db_data)
        except Exception as e:
            return {"error": "Unexpected error", "message": str(e)}

        

    @http.route("/api1/auth/token", methods=["POST"], type="json", auth="public", csrf=False)
    def token(self, **post):
        """The token URL to be used for getting the access_token:

        Args:
            **post must contain login and password.
        Returns:

            returns https response code 404 if failed error message in the body in json format
            and status code 202 if successful with the access_token.
        Example:
           import requests

           headers = {'content-type': 'text/plain', 'charset':'utf-8'}

           data = {
               'login': 'admin',
               'password': 'admin',
               'db': 'galago.ng'
            }
           base_url = 'http://odoo.ng'
           eq = requests.post(
               '{}/api/auth/token'.format(base_url), data=data, headers=headers)
           content = json.loads(req.content.decode('utf-8'))
           headers.update(access-token=content.get('access_token'))
        """
        
        payload = request.httprequest.data.decode()
        payload = json.loads(payload)

        _token = request.env["api.access_token"]
        params = ["db", "login", "password"]
        # params = {key: post.get(key) for key in payload if post.get(key)}
        db, username, password = (
            payload.get("db"),
            payload.get("login"),
            payload.get("password"),
        )
        _credentials_includes_in_body = all([db, username, password])
        if not _credentials_includes_in_body:
            # The request post body is empty the credetials maybe passed via the headers.
            headers = request.httprequest.headers
            db = headers.get("db")
            username = headers.get("login")
            password = headers.get("password")
            _credentials_includes_in_headers = all([db, username, password])
            if not _credentials_includes_in_headers:
                # Empty 'db' or 'username' or 'password:
                return invalid_response(
                    "missing error", "either of the following are missing [db, username,password]", 403,
                )
        # Login in odoo database:
        try:
            request.session.authenticate(db, username, password)
        except AccessError as aee:
            return invalid_response("Access error", "Error: %s" % aee.name)
        except AccessDenied as ade:
            return invalid_response("Access denied", "Login, password or db invalid")
        except Exception as e:
            # Invalid database:
            info = "The database name is not valid {}".format((e))
            error = "invalid_database"
            _logger.error(info)
            return invalid_response("wrong database name", error, 403)

        uid = request.session.uid
        user = request.env['res.users'].sudo().browse(uid)

        # # Check if the user belongs to a specific group
        # # Replace 'external_id_of_the_group' with the actual external ID of the group you're checking
        is_in_teacher = user.has_group('school.group_school_teacher')
        is_in_parent = user.has_group('school.group_school_parent')

        # odoo login failed:
        if not uid:
            info = "authentication failed"
            error = "authentication failed"
            _logger.error(info)
            return invalid_response(401, error, info)

        # Generate tokens
        user_name = user.name  
        user_image = user.image_1920  
        # Convert image to a base64 string if needed
        user_image_base64 = user_image and user_image.decode('utf-8') or None
        employee = request.env["hr.employee"].sudo().search([("user_id", "=", uid)], limit=1)
        hr_employee_id = employee.id if employee else None
        user_email = user.email

        # Generate token
        access_token = _token.find_one_or_create_token(user_id=uid, create=True)

        # Successful response:
        return {
            "uid": uid,
            "partner_id": request.env.user.partner_id.id,
            "access_token": access_token,
            "user_email": user_email,
            "is_in_teacher": is_in_teacher,
            "is_in_parent": is_in_parent,
            "user_name": user_name,
            "user_image": user.image_1920 , 
            "hr_employee_id": hr_employee_id,
        }
        werkzeug.wrappers.Response(
            status=200,
            content_type="application/json; charset=utf-8",
            headers=[("Cache-Control", "no-store"), ("Pragma", "no-cache")],
            response=json.dumps(
                {
                    "uid": uid,
                    # "user_context": request.session.get_context() if uid else {},
                    # "company_id": request.env.user.company_id.id if uid else None,
                    # "company_ids": request.env.user.company_ids.ids if uid else None,
                    "partner_id": request.env.user.partner_id.id,
                    "access_token": access_token,
                    # "company_name": request.env.user.company_name,
                    # "currency": request.env.user.currency_id.name,
                    # "company_name": request.env.user.company_name,
                    # "country": request.env.user.country_id.name,
                    # "contact_address": request.env.user.contact_address,
                    # "customer_rank": request.env.user.customer_rank,
                }
            ),
        )

    @http.route("/api/auth/token", methods=["DELETE"], type="http", auth="none", csrf=False)
    def delete(self, **post):
        """Delete a given token"""
        token = request.env["api.access_token"]
        access_token = post.get("access_token")
        access_token = token.search([("token", "=", access_token)], limit)
        if not access_token:
            error = "Access token is missing in the request header or invalid token was provided"
            return invalid_response(400, error)
        for token in access_token:
            token.unlink()
        # Successful response:
        return valid_response([{"message": "access token %s successfully deleted" % (access_token,), "delete": True}])
