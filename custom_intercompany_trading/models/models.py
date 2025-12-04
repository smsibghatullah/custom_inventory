# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class custom_intercompany_sales(models.Model):
#     _name = 'custom_intercompany_sales.custom_intercompany_sales'
#     _description = 'custom_intercompany_sales.custom_intercompany_sales'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

