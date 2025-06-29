# from odoo import http, fields
# from odoo.http import request
# from odoo.exceptions import AccessError, MissingError


# class CustomPortalController(http.Controller):

#     @http.route(['/my/orders/<int:order_id>'], type='http', auth="public", website=True)
#     def portal_order_page(
#         self,
#         order_id,
#         report_type=None,
#         access_token=None,
#         message=False,
#         download=False,
#         **kw
#     ):
#         try:
#             order_sudo = request.env['sale.order'].sudo()._document_check_access(order_id, access_token=access_token)
#         except (AccessError, MissingError):
#             return request.redirect('/my')

#         # Generate and return PDF
#         if report_type == 'pdf':
#             report = request.env.ref('sale.action_report_saleorder')  # ✅ Correct XML ID

#             pdf_content, _ = report._render_qweb_pdf([order_sudo.id])  # Must be list

#             # Set filename as Sale Order name (e.g., SO023.pdf)
#             filename = "%s.pdf" % order_sudo.name.replace('/', '_')

#             return request.make_response(
#                 pdf_content,
#                 headers=[
#                     ('Content-Type', 'application/pdf'),
#                     ('Content-Length', len(pdf_content)),
#                     (
#                         'Content-Disposition',
#                         'attachment; filename="%s"' % filename
#                         if download else
#                         'inline; filename="%s"' % filename
#                     ),
#                 ]
#             )

#         # Regular view logic (not PDF)
#         backend_url = f'/web#model=sale.order&id={order_sudo.id}&view_type=form'
#         values = {
#             'sale_order': order_sudo,
#             'report_type': 'html',
#             'message': message,
#             'backend_url': backend_url,
#             'res_company': order_sudo.company_id,
#         }

#         return request.render('sale.sale_order_portal_template', values)
