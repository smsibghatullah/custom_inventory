from odoo import models, fields, api,_
from odoo.exceptions import UserError
import base64


class DynamicFieldText(models.Model):
    _name = 'dynamic.field.text'
    _description = 'Dynamic field for text'

    brand_id = fields.Many2one('brand.master', string='Brand', ondelete='cascade')
    sale_order_id = fields.Many2one('sale.order', string='sale', ondelete='cascade')

    text_field = fields.Char('')
    text_value = fields.Char('')


class DynamicFieldCheckbox(models.Model):
    _name = 'dynamic.field.checkbox'
    _description = 'Dynamic field for checkbox'

    brand_id = fields.Many2one('brand.master', string='Brand', ondelete='cascade')
    sale_order_id = fields.Many2one('sale.order', string='sale', ondelete='cascade')
    checkbox_field = fields.Char('')
    checkbox_value = fields.Boolean('')


class DynamicFieldSelection(models.Model):
    _name = 'dynamic.field.selection.key'
    _description = 'Dynamic field for selection'

    selection_field = fields.Char('')
    # sale_order_id = fields.Many2one('sale.order', string='sale', ondelete='cascade')
    brand_id = fields.Many2one('brand.master', string='Brand', ondelete='cascade')

    selection_value = fields.One2many('dynamic.field.selection.values', 'key_field')
    selection_value_ids = fields.One2many('dynamic.field.selection.values', 'key_field',
                                          compute='_compute_selection_value_ids')
    selected_value = fields.Many2one('dynamic.field.selection.values', domain="[('id', 'in', selection_value_ids)]")


    @api.depends('selection_value')
    def _compute_selection_value_ids(self):
        for record in self:
            print("sssssssssssssssss")
            if record.selection_value:
                record.selection_value_ids = record.selection_value.ids
            else:
                record.selection_value_ids =  [(5,)]

# class DynamicSaleOrderFieldSelection(models.Model):
#     _name = 'dynamic.saleorder.selection.key'
#     _description = 'Dynamic field for selection'
#
#     selection_field = fields.Char('Kay')
#     sale_order_id = fields.Many2one('sale.order', string='sale')
#     selected_value = fields.Many2one('dynamic.field.selection.values', domain="[('sale_order_options', '=', id)]")
#


    # @api.depends('selection_value')
    # def _get_domain_for_selected_value(self):
    #     for record in self:
    #         if record.selection_value:
    #             # Get the IDs from the related One2many field
    #             selection_value_ids = record.selection_value.ids
    #             return [('id', 'in', selection_value_ids)]
    #         return []
    #
    #
    # @api.onchange('selected_value')
    # def _onchange_selected_value(self):
    #     for line in self:
    #         if line.selection_value:
    #             return  {'domain': {'selected_value': line.selection_value.ids}}
    #         else:
    #             return {'domain': {'selected_value': []}}

class DynamicFieldSelectionValues(models.Model):
    _name = 'dynamic.field.selection.values'
    _description = 'Dynamic field for selection_values'
    _rec_name = 'value_field'

    value_field = fields.Char('')
    key_field = fields.Many2one('dynamic.field.selection.key')
    # sale_order_options = fields.Many2one('dynamic.saleorder.selection.key')