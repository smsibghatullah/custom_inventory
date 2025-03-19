from odoo import models, fields, api,_
from odoo.exceptions import UserError

class ProductCostWizard(models.TransientModel):
    _name = 'product.cost.wizard'
    _description = 'Product Cost Wizard'

    product_id = fields.Many2one('product.product', string="Product", required=True)
    product_cost = fields.Float(string="Product Cost", required=True)
    total_qty = fields.Float(string="Total Quantity", required=True)
    new_expenses_cost = fields.Integer(string="New Expenses Cost", required=True)

    @api.model
    def default_get(self, fields):
        res = super(ProductCostWizard, self).default_get(fields)
        product_id = self.env.context.get('default_product_id')
        product = self.env['product.product'].browse(product_id)
        res.update({
            'product_id': product_id,
            'product_cost': product.avg_cost,  
            'total_qty': product.qty_available,  
        })
        return res

    def action_save(self):
        for record in self:
            print("yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy")
            if record.total_qty != 0 and record.new_expenses_cost != 0:
                expense_per_qty = record.new_expenses_cost / record.total_qty
                new_cost = record.product_cost + expense_per_qty
            elif record.new_expenses_cost == 0:
                raise UserError(_("Expense cannot be zero."))
            else:
                raise UserError(_("Please ensure that total quantity and expenses cost are not zero."))
            print("eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")
            product = record.product_id
            product.write({
                'standard_price': new_cost, 
                'default_product_cost': record.product_cost if product.default_product_cost == False else product.default_product_cost ,
                'lst_price' : new_cost
            })
            print(product.standard_price,"kkkkkkkkkkkkkkkkkkkkkk",new_cost,"pppppppppppppppppp")
            message = f"Last Price: {record.product_cost}\n" \
                      f" | New Cost: {new_cost:.2f}\n" \
                      f" | Quantity: {record.total_qty}\n" \
                      f" | Expense: {record.new_expenses_cost}\n" \
                      f" | Updated by: {self.env.user.name}"

            product.message_post(body=message, message_type='notification', subtype_xmlid='mail.mt_comment')

        return {'type': 'ir.actions.act_window_close'}

class ProductProduct(models.Model):
    _inherit = 'product.product'

    default_product_cost = fields.Float(string="Product Original Cost", required=True)

    def open_product_cost_wizard(self):
        return {
            'name':'Product Expense Wizard',
            'type': 'ir.actions.act_window',
            'res_model': 'product.cost.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('custom_inventory.view_product_cost_wizard').id,
            'target': 'new',
            'context': {
                'default_product_id': self.id,
                'default_product_cost':self.avg_cost,
                'default_total_qty': self.total_value
            }
        }
