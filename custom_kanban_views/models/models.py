# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class custom_kanban_views(models.Model):
#     _name = 'custom_kanban_views.custom_kanban_views'
#     _description = 'custom_kanban_views.custom_kanban_views'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

