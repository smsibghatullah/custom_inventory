import json
import logging

import werkzeug.wrappers

from odoo import http
from odoo.addons.restful.common import invalid_response, valid_response
from odoo.exceptions import AccessDenied, AccessError
from odoo.http import request
import base64

_logger = logging.getLogger(__name__)


class AccessToken(http.Controller):
    """."""

    def __init__(self):

        self._token = request.env["api.access_token"]


    @http.route('/api/shift.attendance/create', type="json", auth="public", methods=["POST"], csrf=False)
    def post(self, **payload):
        try:
            access_token = request.httprequest.headers.get("access_token")
            if not access_token:
                return invalid_response("access_token_not_found", "Missing access token in request header", 401)

            access_token_data = (
                request.env["api.access_token"].sudo().search([("token", "=", access_token)], order="id DESC", limit=1)
            )

            if not access_token_data or access_token_data.token != access_token:
                return invalid_response("access_token_invalid", "Token is expired or invalid", 401)

            _logger.info("User authenticated: %s", access_token_data.user_id.id)

            # Set user in session and update request environment
            request.session.uid = access_token_data.user_id.id
            request.update_env(user=access_token_data.user_id)

            # Decode JSON payload
            payload = request.httprequest.data.decode()
            payload = json.loads(payload)
            _logger.info("Received payload: %s", payload)

            # Get shift.attendance model
            model = request.env['shift.attendance'].sudo()

            # Prepare values for record creation
            values = {}
            for k, v in payload.items():
                if "__api__" in k:
                    values[k[7:]] = ast.literal_eval(v)
                else:
                    values[k] = v

            _logger.info("Creating shift attendance with values: %s", values)

            # Create shift attendance record
            resource = model.create(values)

            _logger.info("Record created: %s", resource)

            # Return successful response
            return valid_response(resource.read())

        except Exception as e:
            request.env.cr.rollback()
            _logger.error("Error creating shift attendance: %s", str(e))
            return invalid_response("error", str(e))
        

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

        # Generate token
        access_token = _token.find_one_or_create_token(user_id=uid, create=True)

        # Successful response:
        return {
            "uid": uid,
            "partner_id": request.env.user.partner_id.id,
            "access_token": access_token,
            "is_in_teacher": is_in_teacher,
            "is_in_parent": is_in_parent,
            "user_name": user_name,
            "user_image": user_image_base64, 
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
