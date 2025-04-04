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
                print(expense_per_qty,"mmmmmmmmmmmmmmmmmmmm",record.product_cost + expense_per_qty)
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
                'avg_cost':new_cost
            })
            print(product.standard_price,"kkkkkkkkkkkkkkkkkkkkkk",new_cost,"pppppppppppppppppp",product.avg_cost)
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

    @api.depends('stock_valuation_layer_ids')
    @api.depends_context('to_date', 'company')
    def _compute_value_svl(self):
        """Compute totals of multiple svl related values"""
        company_id = self.env.company
        self.company_currency_id = company_id.currency_id
        domain = [
            *self.env['stock.valuation.layer']._check_company_domain(company_id),
            ('product_id', 'in', self.ids),
        ]
        if self.env.context.get('to_date'):
            to_date = fields.Datetime.to_datetime(self.env.context['to_date'])
            domain.append(('create_date', '<=', to_date))
        groups = self.env['stock.valuation.layer']._read_group(
            domain,
            groupby=['product_id'],
            aggregates=['value:sum', 'quantity:sum'],
        )
        # Browse all products and compute products' quantities_dict in batch.
        group_mapping = {product: aggregates for product, *aggregates in groups}
        for product in self:
            print(product.standard_price,"ppppppppppppppppppppp")
            value_sum, quantity_sum = group_mapping.get(product._origin, (0, 0))
            value_svl = company_id.currency_id.round(value_sum)
            avg_cost = product.standard_price
            product.value_svl = value_svl
            product.quantity_svl = quantity_sum
            product.avg_cost = avg_cost
            product.total_value = avg_cost * product.sudo(False).qty_available

    def _prepare_out_svl_vals(self, quantity, company):
        """Prepare the values for a stock valuation layer created by a delivery.

        :param quantity: the quantity to value, expressed in `self.uom_id`
        :return: values to use in a call to create
        :rtype: dict
        """
        self.ensure_one()
        company_id = self.env.context.get('force_company', self.env.company.id)
        company = self.env['res.company'].browse(company_id)
        currency = company.currency_id
        # Quantity is negative for out valuation layers.
        quantity = -1 * quantity
        vals = {
            'product_id': self.id,
            'value': currency.round(quantity * self.standard_price),
            'unit_cost': self.standard_price,
            'quantity': quantity,
        }
        # fifo_vals = self._run_fifo(abs(quantity), company)
        # vals['remaining_qty'] = fifo_vals.get('remaining_qty')
        # In case of AVCO, fix rounding issue of standard price when needed.
        if self.product_tmpl_id.cost_method == 'average' and not float_is_zero(self.quantity_svl, precision_rounding=self.uom_id.rounding):
            rounding_error = currency.round(
                (self.standard_price * self.quantity_svl - self.value_svl) * abs(quantity / self.quantity_svl)
            )
            if rounding_error:
                # If it is bigger than the (smallest number of the currency * quantity) / 2,
                # then it isn't a rounding error but a stock valuation error, we shouldn't fix it under the hood ...
                if abs(rounding_error) <= max((abs(quantity) * currency.rounding) / 2, currency.rounding):
                    vals['value'] += rounding_error
                    vals['rounding_adjustment'] = '\nRounding Adjustment: %s%s %s' % (
                        '+' if rounding_error > 0 else '',
                        float_repr(rounding_error, precision_digits=currency.decimal_places),
                        currency.symbol
                    )
        # if self.product_tmpl_id.cost_method == 'fifo':
        #     vals.update(fifo_vals)
        return vals

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
