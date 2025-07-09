# -*- coding: utf-8 -*-
# from odoo import http


# class CustomKanbanViews(http.Controller):
#     @http.route('/custom_kanban_views/custom_kanban_views', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_kanban_views/custom_kanban_views/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_kanban_views.listing', {
#             'root': '/custom_kanban_views/custom_kanban_views',
#             'objects': http.request.env['custom_kanban_views.custom_kanban_views'].search([]),
#         })

#     @http.route('/custom_kanban_views/custom_kanban_views/objects/<model("custom_kanban_views.custom_kanban_views"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_kanban_views.object', {
#             'object': obj
#         })

