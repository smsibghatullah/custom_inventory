# -*- coding: utf-8 -*-
# from odoo import http


# class CustomIntercompanySales(http.Controller):
#     @http.route('/custom_intercompany_sales/custom_intercompany_sales', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_intercompany_sales/custom_intercompany_sales/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_intercompany_sales.listing', {
#             'root': '/custom_intercompany_sales/custom_intercompany_sales',
#             'objects': http.request.env['custom_intercompany_sales.custom_intercompany_sales'].search([]),
#         })

#     @http.route('/custom_intercompany_sales/custom_intercompany_sales/objects/<model("custom_intercompany_sales.custom_intercompany_sales"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_intercompany_sales.object', {
#             'object': obj
#         })

