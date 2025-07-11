from odoo import models, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super().read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

        if groupby and groupby[0] == 'payment_state':
            custom_order = ['paid', 'un_paid', 'partialpaid']

            def get_payment_state(group):
                for condition in group.get('__domain', []):
                    if isinstance(condition, (list, tuple)) and len(condition) >= 3:
                        if condition[0] == 'payment_state' and condition[1] == '=':
                            return condition[2]
                return None

            res.sort(
                key=lambda g: custom_order.index(get_payment_state(g)) if get_payment_state(g) in custom_order else len(custom_order)
            )

        return res
