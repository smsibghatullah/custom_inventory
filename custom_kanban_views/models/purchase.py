from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # ✅ Override the state field to enable group_expand
    state = fields.Selection(
        selection=[
            ('draft', 'RFQ'),
            ('sent', 'RFQ Sent'),
            ('to approve', 'To Approve'),
            ('purchase', 'Purchase Order'),
            ('done', 'Locked'),
            ('cancel', 'Cancelled'),
        ],
        string='Status',
        readonly=True,
        index=True,
        copy=False,
        tracking=True,
        default='draft',
        group_expand='_read_group_state_ids',
    )

    @api.model
    def _read_group_state_ids(self, states, domain, orderby=''):
        """Ensure all purchase order states appear in Kanban even with no records."""
        return [key for key, _ in self.fields_get(allfields=['state'])['state']['selection']]

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super().read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

        if groupby and groupby[0] == 'state':
            custom_order = ['draft', 'sent', 'to approve', 'purchase', 'done', 'cancel']

            def get_state_from_domain(group):
                for condition in group.get('__domain', []):
                    if isinstance(condition, (list, tuple)) and len(condition) >= 3:
                        if condition[0] == 'state' and condition[1] == '=':
                            return condition[2]
                return None

            res.sort(
                key=lambda g: custom_order.index(get_state_from_domain(g)) if get_state_from_domain(g) in custom_order else len(custom_order)
            )

        return res
