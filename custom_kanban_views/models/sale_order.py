from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_manual_conversion = fields.Boolean(string="Converted Manually", default=False)
    total_product_qty = fields.Float(string="Total Quantity", compute="_compute_total_product_qty", store=True)

    # ✅ Override state field to support group_expand for Kanban
    state = fields.Selection(
        selection=[
            ('draft', 'Quotation'),
            ('sent', 'Quotation Sent'),
            ('sale', 'Sales Order'),
            ('done', 'Locked'),
            ('cancel', 'Cancelled'),
        ],
        string='Status',
        readonly=True,
        copy=False,
        index=True,
        tracking=3,
        default='draft',
        group_expand='_read_group_state_ids',
    )

    @api.model
    def _read_group_state_ids(self, states, domain, orderby=''):
        """Ensure all sale states show in kanban, even with no records."""
        return [key for key, _ in self.fields_get(allfields=['state'])['state']['selection']]

    @api.depends('order_line.product_uom_qty')
    def _compute_total_product_qty(self):
        for order in self:
            order.total_product_qty = sum(order.order_line.mapped('product_uom_qty'))

    def action_confirm(self):
        for order in self:
            order.is_manual_conversion = True
            order.is_email_conversion = False
        return super(SaleOrder, self).action_confirm()

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super(SaleOrder, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        
        if groupby and groupby[0] == 'state':
            custom_order = ['draft', 'sent', 'sale', 'done', 'cancel']
            res.sort(key=lambda x: custom_order.index(x['state']) if x['state'] in custom_order else len(custom_order))
        
        return res
