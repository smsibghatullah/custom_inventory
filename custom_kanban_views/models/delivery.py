from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    sale_order_status = fields.Selection(
        related='sale_id.state',
        string="Sale Order Status",
        store=False
    )

    invoice_status = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('posted', 'Posted'),
            ('cancel', 'Cancelled'),
            ('no_invoice', 'No Invoice'),
        ],
        string="Invoice Status",
        compute='_compute_invoice_status',
        store=False
    )

    payment_status = fields.Selection(
        selection=[
            ('not_paid', 'Not Paid'),
            ('partial', 'Partially Paid'),
            ('in_payment', 'In Payment'),
            ('paid', 'Paid'),
            ('reversed', 'Reversed'),
            ('no_invoice', 'No Invoice'),
        ],
        string="Payment Status",
        compute='_compute_payment_status',
        store=False
    )

    tag_ids = fields.Many2many(
        'crm.tag',
        'delivery_id_seq',  
        string='Tags',
        help='Select the brands associated with this delivery'
    )

    available_tag_ids = fields.Many2many(
        'crm.tag',
        compute="_compute_available_tags",
        string="Available Tags"
    )
    sale_order_reference = fields.Char(related='sale_id.reference',string="Sale Order Reference")

    margin = fields.Float(string="Sales Margin", compute='_compute_margin', store=True)

    has_negative_margin = fields.Boolean(string="Negative Margin", compute="_compute_negative_margin")

    @api.depends('margin')
    def _compute_negative_margin(self):
        for rec in self:
            rec.has_negative_margin = rec.margin < 0

    @api.depends('sale_id')
    def _compute_margin(self):
        for picking in self:
            picking.margin = picking.sale_id.margin or 0.0


    @api.depends('tag_ids')
    def _compute_available_tags(self):
        for record in self:
            record.available_tag_ids = self.env.user.tag_ids

    @api.depends('sale_id')
    def _compute_invoice_status(self):
        for picking in self:
            invoices = picking.sale_id.invoice_ids
            if not invoices:
                picking.invoice_status = 'no_invoice'
            else:
                states = invoices.mapped('state')
                if len(set(states)) == 1:
                    picking.invoice_status = states[0]
                else:
                    picking.invoice_status = 'posted'

    @api.depends('sale_id')
    def _compute_payment_status(self):
        for picking in self:
            invoices = picking.sale_id.invoice_ids
            if not invoices:
                picking.payment_status = 'no_invoice'
            else:
                states = invoices.mapped('payment_state')
                if len(set(states)) == 1:
                    picking.payment_status = states[0]
                else:
                    picking.payment_status = 'partial'

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super(StockPicking, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        
        if groupby and groupby[0] == 'state':
            custom_order = ['draft', 'waiting', 'confirmed', 'assigned','pick_pack','ready_for_pickup','picked_up_by_logistic','pickup_by_buyer','in_transit','delivered','done','cancel']
            res.sort(key=lambda x: custom_order.index(x['state']) if x['state'] in custom_order else len(custom_order))
        
        return res


