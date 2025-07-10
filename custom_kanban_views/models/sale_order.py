from odoo import models,fields,api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_manual_conversion = fields.Boolean(string="Converted Manually", default=False)
    total_product_qty = fields.Float(string="Total Quantity", compute="_compute_total_product_qty", store=True)

    @api.depends('order_line.product_uom_qty')
    def _compute_total_product_qty(self):
        for order in self:
            order.total_product_qty = sum(order.order_line.mapped('product_uom_qty'))
    

    def action_confirm(self):
        for order in self:
            order.is_manual_conversion = True  
            order.is_email_conversion = False 
        return super(SaleOrder, self).action_confirm()


