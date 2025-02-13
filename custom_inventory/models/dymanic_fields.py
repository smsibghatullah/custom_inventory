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

class DynamicSaleOrderFieldSelection(models.Model):
    _name = 'dynamic.saleorder.selection.key'
    _description = 'Dynamic field for selection'

    selection_field = fields.Char('Key')
    sale_order_id = fields.Many2one('sale.order', string='sale')
    # selected_value = fields.Many2one('dynamic.field.selection.values.sale' )
    options_value = fields.One2many('dynamic.field.selection.values.sale', 'key_field')
    sale_random_key = fields.Float()
    selected_value = fields.Many2one(
        'dynamic.field.selection.values.sale',
        string='Selected Value',
        domain="[('key_field_parent', '=', selection_field),('key_field','=',id)]"
    )


class DynamicFieldSelectionValuesSale(models.Model):
    _name = 'dynamic.field.selection.values.sale'
    _description = 'Dynamic field for selection_values'
    _rec_name = 'value_field'

    value_field = fields.Char('')
    key_field_parent = fields.Char('')
    sale_random_key = fields.Float()
    key_field = fields.Many2one('dynamic.saleorder.selection.key')


class DynamicFieldSelectionValues(models.Model):
    _name = 'dynamic.field.selection.values'
    _description = 'Dynamic field for selection_values'
    _rec_name = 'value_field'

    value_field = fields.Char('')
    key_field = fields.Many2one('dynamic.field.selection.key')
    # sale_order_options = fields.Many2one('dynamic.saleorder.selection.key')