import json
import logging

import werkzeug.wrappers
from odoo import http, models, fields
from odoo import http
from odoo.addons.restful.common import (extract_arguments, invalid_response,
                                        valid_response, extract_arguments_sibghat)
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

    @http.route(
        '/api/survey/user_input/answers',
        type="http",
        auth="none",
        methods=["GET"],
        csrf=False
    )
    def get_answers(self, **payload):
        try:
            model = request.env['ir.model'].sudo().search(
                [("model", "=", "survey.user_input.line")],
                limit=1
            )

            if not model:
                return invalid_response(
                    "invalid object model",
                    "The model is not available in the registry.",
                )

            domain, fields, offset, limit, order = extract_arguments_sibghat(payload)

            lines = request.env[model.model].sudo().search(
                domain=domain,
                offset=offset,
                limit=limit,
                order=order
            )

            answers = []

            for line in lines:
                ans = line.read(fields or [])  # read returns list
                ans = ans[0] if ans else {}

                # ================= TABLE =================
                if ans.get("answer_type") == "table":
                    table_records = []
                    for table_line in line.table_ids:
                        table_records.append({
                            "id": table_line.id,
                            "row_no": table_line.row_no,
                            "column_no": table_line.column_no,
                            "column_name": table_line.column_name,
                            "value": table_line.value,
                        })
                    ans["table_ids"] = table_records

                # ================= RISK =================
                elif ans.get("answer_type") == "risk":
                    risk_records = []
                    for hazard in line.hazard_ids:  # hazard_ids Many2many
                        # Fetch the full hazard record
                        hazard_obj = request.env['survey.potential_hazard'].sudo().browse(hazard.id)
                        if not hazard_obj:
                            continue

                        risk_records.append({
                            "question_id": line.question_id.id,
                            "hazard_id": hazard_obj.id,
                            "hazard_name": hazard_obj.name,
                            "hazard_consequence": {
                                "id": hazard_obj.hazard_consequence_id.id if hazard_obj.hazard_consequence_id else None,
                                "name": hazard_obj.hazard_consequence_id.name if hazard_obj.hazard_consequence_id else None,
                                "rating": hazard_obj.hazard_consequence_id.rating if hazard_obj.hazard_consequence_id else None,
                            },
                            "likelihood": {
                                "id": hazard_obj.likelihood_id.id if hazard_obj.likelihood_id else None,
                                "name": hazard_obj.likelihood_id.name if hazard_obj.likelihood_id else None,
                                "rating": hazard_obj.likelihood_id.rating if hazard_obj.likelihood_id else None,
                            },
                            "initial_risk": {
                                "score": hazard_obj.initial_risk_score,
                                "level": hazard_obj.initial_risk_level,
                            },
                            "controls": [
                                {"id": control.id, "name": control.name} 
                                for control in hazard_obj.control_ids
                            ],
                            "post_control_hazard_consequence": {
                                "id": hazard_obj.post_control_hazard_consequence_id.id if hazard_obj.post_control_hazard_consequence_id else None,
                                "name": hazard_obj.post_control_hazard_consequence_id.name if hazard_obj.post_control_hazard_consequence_id else None,
                                "rating": hazard_obj.post_control_hazard_consequence_id.rating if hazard_obj.post_control_hazard_consequence_id else None,
                            },
                            "post_control_likelihood": {
                                "id": hazard_obj.post_control_likelihood_id.id if hazard_obj.post_control_likelihood_id else None,
                                "name": hazard_obj.post_control_likelihood_id.name if hazard_obj.post_control_likelihood_id else None,
                                "rating": hazard_obj.post_control_likelihood_id.rating if hazard_obj.post_control_likelihood_id else None,
                            },
                            "post_control_risk": {
                                "score": hazard_obj.post_control_risk_score,
                                "level": hazard_obj.post_control_risk_level,
                            },
                        })
                        print(risk_records,"=====================================12222222222222222222222222222")

                    ans["hazard_ids"] = risk_records

                answers.append(ans)

            # user_input header
            user_input = lines[:1].user_input_id if lines else False
            response = {
                "user_input": {
                    "id": user_input.id if user_input else False,
                    "survey_id": [
                        user_input.survey_id.id,
                        user_input.survey_id.display_name
                    ] if user_input else False,
                },
                "answers": answers,
            }

            return valid_response(response)

        except AccessError as e:
            return invalid_response("Access error", "Error: %s" % e.name)


    @http.route('/api/survey/potential_hazard/create', type='json', auth='user', methods=['POST'], csrf=False)
    def create_potential_hazard(self, **kwargs):
        try:
            payload = request.httprequest.data.decode()
            payload = json.loads(payload or "{}")

            if not payload:
                return {"success": False, "error": "No data provided"}

            required_fields = ['name']
            for field in required_fields:
                if field not in payload:
                    return {"success": False, "error": f"Missing field: {field}"}

            hazard_vals = {
                'name': payload.get('name'),
                'hazard_consequence_id': payload.get('hazard_consequence_id') or False,
                'likelihood_id': payload.get('likelihood_id') or False,
                'post_control_hazard_consequence_id': payload.get('post_control_hazard_consequence_id') or False,
                'post_control_likelihood_id': payload.get('post_control_likelihood_id') or False,
                'control_ids': payload.get('control_ids') or [],
            }

            hazard_record = request.env['survey.potential_hazard'].sudo().create(hazard_vals)

            _logger.info("Survey potential hazard created with ID %s", hazard_record.id)

            return {"success": True, "message": "Potential hazard created", "hazard_id": hazard_record.id}

        except Exception as e:
            _logger.exception("Error creating potential hazard")
            return {"success": False, "error": str(e)}


    @http.route('/api/survey/table/create', type='json', auth='user', methods=['POST'], csrf=False)
    def create_survey_table(self, **kwargs):
        try:
            payload = request.httprequest.data.decode()
            payload = json.loads(payload or "{}")

            if not payload:
                return {
                    "success": False,
                    "error": "No data provided"
                }

            required_fields = ['row_no', 'column_no', 'value']
            for field in required_fields:
                if field not in payload:
                    return {
                        "success": False,
                        "error": "Missing field: %s" % field
                    }

            table_vals = {
                'row_no': payload.get('row_no'),
                'column_no': payload.get('column_no'),
                'column_name': payload.get('column_name', False),
                'value': payload.get('value'),
            }

            table_record = request.env['survey.table'].sudo().create(table_vals)

            _logger.info("Survey table created with ID %s", table_record.id)

            return {
                "success": True,
                "message": "Survey table row created",
                "table_id": table_record.id
            }

        except Exception as e:
            _logger.exception("Error creating survey table")
            return {
                "success": False,
                "error": str(e)
            }    
        
    @http.route('/api/send_survey_via_email', type='json', auth='user', methods=['POST'], csrf=False)
    def send_survey_via_email(self, **kwargs):

        payload_str = request.httprequest.data.decode()
        try:
            payload = json.loads(payload_str or "{}")
        except Exception as e:
            return {"success": False, "error": f"Invalid JSON: {str(e)}"}

        user_input_ids = payload.get("user_input_ids", [])
        recipient_ids = payload.get("recipients", [])
        cc_emails = payload.get("cc", []) or payload.get("ccEmail", [])

        if not user_input_ids:
            return {"success": False, "error": "No survey inputs provided"}

        # 🔑 SAME REPORT AS WIZARD
        report_action = request.env.ref('custom_inventory.action_report_employment_certificate')

        attachments = []
        company = None

        for u_input_id in user_input_ids:
            user_input = request.env['survey.user_input'].sudo().browse(u_input_id)
            if not user_input.exists():
                continue

            # ---- Generate PDF (ODOO 17 CORRECT WAY) ----
            pdf_content, _ = report_action._render_qweb_pdf(
                report_action.report_name,
                res_ids=[user_input.id]
            )

            attachment = request.env['ir.attachment'].sudo().create({
                'name': f"{user_input.survey_id.title or 'Survey'}_{user_input.id}.pdf",
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': 'survey.user_input',
                'res_id': user_input.id,
                'mimetype': 'application/pdf',
            })

            attachments.append(attachment.id)

            # ----- Get company from first valid user_input -----
            if not company:
                if user_input.project_id:
                    company = user_input.project_id.company_id
                elif user_input.task_id and user_input.task_id.project_id:
                    company = user_input.task_id.project_id.company_id

        # fallback to logged in user's company
        if not company:
            company = request.env.user.company_id

        # -------- Send Email --------
        mail_values = {
            'subject': "Survey Results",
            'body_html': f"""
                <p>Dear User,</p>
                <p>Please find attached your survey result report(s).</p>
                <p>Best regards,<br/>{company.name}</p>
            """,
            'email_to': ','.join(recipient_ids) if isinstance(recipient_ids, list) else recipient_ids,
            'email_cc': ','.join(cc_emails) if cc_emails else False,
            'email_from': company.brand_email or request.env.user.email_formatted,
            'attachment_ids': [(6, 0, attachments)],
        }

        mail = request.env['mail.mail'].sudo().create(mail_values)
        mail.send()

        return {
            "success": True,
            "message": "Survey PDFs sent successfully"
        }



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
            # for line in survey_input.sudo().user_input_line_ids:
            #     line.hazard_ids = [(5, 0, 0)]

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

            questions = request.env['survey.question'].sudo().search([
                ('id', 'in', survey.question_ids.ids)
            ])

            grouped_data = {}

            for question in questions:

                group = question.group_id
                group_id = group.id if group else 0
                group_name = group.name if group else ""

                if group_id not in grouped_data:
                    grouped_data[group_id] = {
                        "group_id": group_id,
                        "group_name": group_name,
                        "heading": {}
                    }

                heading = question.heading_id
                heading_id = heading.id if heading else 0
                heading_name = heading.name if heading else ""

                if heading_id not in grouped_data[group_id]["heading"]:
                    grouped_data[group_id]["heading"][heading_id] = {
                        "heading_id": heading_id,
                        "heading_name": heading_name,
                        "questions": []
                    }

                answer_ids = (
                    question.suggested_answer_ids.ids +
                    question.matrix_row_ids.ids
                )

                answers = request.env['survey.question.answer'].sudo().search([
                    ('id', 'in', answer_ids)
                ])

                answers_data = [{
                    "answer_id": ans.id,
                    "answer_value": ans.value,
                    "answer_type": ans.question_type,
                } for ans in answers]

                table_data = []
                print(question.question_type,"question.question_type")
                if question.question_type == 'table':
                    print(question.title,question.id,"question.table_ids=======================",question.table_ids)
                    for table_line in question.table_ids:
                        table_data.append({
                            "id": table_line.id,
                            "row_no": table_line.row_no,
                            "column_no": table_line.column_no,
                            "column_name": table_line.column_name,
                            "value": table_line.value,
                        })
                risk = []
                # print(table_data,"table_data====================================")
                if question.question_type == 'risk':
                    for hazard in question.potential_hazard_ids:
                        print(hazard.hazard_consequence_id,"=======================================")
                        risk.append({
                            "question_id":question.id,
                            "hazard_id": hazard.id,
                            "hazard_name": hazard.name,

                            "hazard_consequence": {
                                "id": hazard.hazard_consequence_id.id if hazard.hazard_consequence_id else None,
                                "name": hazard.hazard_consequence_id.name if hazard.hazard_consequence_id else None,
                                "rating": hazard.hazard_consequence_id.rating if hazard.hazard_consequence_id else None,
                            },

                            "likelihood": {
                                "id": hazard.likelihood_id.id if hazard.likelihood_id else None,
                                "name": hazard.likelihood_id.name if hazard.likelihood_id else None,
                                "rating": hazard.likelihood_id.rating if hazard.likelihood_id else None,
                            },

                            "initial_risk": {
                                "score": hazard.initial_risk_score,
                                "level": hazard.initial_risk_level,
                            },

                            "controls": [
                                {
                                    "id": control.id,
                                    "name": control.name,
                                } for control in hazard.control_ids
                            ],

                            "post_control_hazard_consequence": {
                                "id": hazard.post_control_hazard_consequence_id.id if hazard.post_control_hazard_consequence_id else None,
                                "name": hazard.post_control_hazard_consequence_id.name if hazard.post_control_hazard_consequence_id else None,
                                "rating": hazard.post_control_hazard_consequence_id.rating if hazard.post_control_hazard_consequence_id else None,
                            },

                            "post_control_likelihood": {
                                "id": hazard.post_control_likelihood_id.id if hazard.post_control_likelihood_id else None,
                                "name": hazard.post_control_likelihood_id.name if hazard.post_control_likelihood_id else None,
                                "rating": hazard.post_control_likelihood_id.rating if hazard.post_control_likelihood_id else None,
                            },

                            "post_control_risk": {
                                "score": hazard.post_control_risk_score,
                                "level": hazard.post_control_risk_level,
                            },
                        })

                grouped_data[group_id]["heading"][heading_id]["questions"].append({
                    "question_id": question.id,
                    "question_name": question.display_name,
                    "question_type": question.question_type,
                    "subtitle": question.subtitle,
                    "auto_filled": question.auto_filled,
                    "pre_filled": question.pre_filled,
                    "prefill_value": (
                        question.prefill_text if question.pre_filled and question.question_type == 'text_box' else
                        question.prefill_char if question.pre_filled and question.question_type == 'char_box' else
                        question.prefill_number if question.pre_filled and question.question_type == 'numerical_box' else
                        question.prefill_date if question.pre_filled and question.question_type == 'date' else 
                        question.prefill_datetime if question.pre_filled and question.question_type == 'datetime' else 
                        question.prefill_signature if question.pre_filled and question.question_type == 'digital_signature' else
                        None
                    ),
                    "current_date_time":fields.Datetime.now(),
                    "current_date":fields.Date.today(),
                    "refrence_question_id": question.question_id.id,
                    "description": question.description,
                    "answers": answers_data,
                    'risk':risk,
                    'static_content': question.static_content if question.question_type == 'static_content' else '',
                    "table": table_data
                })
               

            result = []
            for group in grouped_data.values():
                group["heading"] = list(group["heading"].values())
                result.append(group)

            response_data = {
                "survey_id": survey.id,
                "survey_title": survey.title,
                "questions_by_heading": result
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
