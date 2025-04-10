from odoo import models, fields, api,_
from odoo.exceptions import UserError
import base64


class PODynamicFieldText(models.Model):
    _name = 'purchase.dynamic.field.text'
    _description = 'Dynamic field for text'

    brand_id = fields.Many2one('brand.master', string='Brand', ondelete='cascade')
    purchase_order_id = fields.Many2one('purchase.order', string='purchase', ondelete='cascade')
    text_field = fields.Char('')
    validation_check = fields.Boolean('')
    text_value = fields.Char('')


class PODynamicFieldCheckbox(models.Model):
    _name = 'purchase.dynamic.field.checkbox'
    _description = 'Dynamic field for checkbox'

    brand_id = fields.Many2one('brand.master', string='Brand', ondelete='cascade')
    purchase_order_id = fields.Many2one('purchase.order', string='purchase', ondelete='cascade')
    checkbox_field = fields.Char('')
    checkbox_value = fields.Boolean('')


class PODynamicFieldSelection(models.Model):
    _name = 'purchase.dynamic.field.selection.key'
    _description = 'Dynamic field for selection'

    selection_field = fields.Char('')
    # purchase_order_id = fields.Many2one('purchase.order', string='purchase', ondelete='cascade')
    brand_id = fields.Many2one('brand.master', string='Brand', ondelete='cascade')

    selection_value = fields.One2many('purchase.dynamic.field.selection.values', 'key_field')
    selection_value_ids = fields.One2many('purchase.dynamic.field.selection.values', 'key_field',
                                          compute='_compute_selection_value_ids')
    selected_value = fields.Many2one('purchase.dynamic.field.selection.values', domain="[('id', 'in', selection_value_ids)]")


    @api.depends('selection_value')
    def _compute_selection_value_ids(self):
        for record in self:
            print("sssssssssssssssss")
            if record.selection_value:
                record.selection_value_ids = record.selection_value.ids
            else:
                record.selection_value_ids =  [(5,)]

class PODynamicSaleOrderFieldSelection(models.Model):
    _name = 'purchase.dynamic.purchaseorder.selection.key'
    _description = 'Dynamic field for selection'

    selection_field = fields.Char('Key')
    purchase_order_id = fields.Many2one('purchase.order', string='purchase')
    # selected_value = fields.Many2one('dynamic.field.selection.values.sale' )
    options_value = fields.One2many('purchase.dynamic.field.selection.values.purchase', 'key_field')
    sale_random_key = fields.Float()
    selected_value = fields.Many2one(
        'purchase.dynamic.field.selection.values.purchase',
        string='Selected Value',
        domain="[('key_field_parent', '=', selection_field),('key_field','=',id)]"
    )


class PODynamicFieldSelectionValuesSale(models.Model):
    _name = 'purchase.dynamic.field.selection.values.purchase'
    _description = 'Dynamic field for selection_values'
    _rec_name = 'value_field'

    value_field = fields.Char('')
    key_field_parent = fields.Char('')
    sale_random_key = fields.Float()
    key_field = fields.Many2one('purchase.dynamic.purchaseorder.selection.key')


class PODynamicFieldSelectionValues(models.Model):
    _name = 'purchase.dynamic.field.selection.values'
    _description = 'Dynamic field for selection_values'
    _rec_name = 'value_field'

    value_field = fields.Char('')
    key_field = fields.Many2one('purchase.dynamic.field.selection.key')
    # sale_order_options = fields.Many2one('dynamic.saleorder.selection.key')

