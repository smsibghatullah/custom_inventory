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
    stage_id = fields.Many2one(
        'stock.picking.stage',
        string='Stage',
        group_expand='_read_group_stage_ids',
    )

    @api.model
    def write(self, vals):
        if 'stage_id' in vals:
            stage = self.env['stock.picking.stage'].browse(vals['stage_id'])
            if stage and stage.code:
                vals['state'] = stage.code 
        return super().write(vals)


    @api.model
    def _read_group_stage_ids(self, stages, domain, orderby='sequence'):
        return self.env['stock.picking.stage'].search([], order=orderby)


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
    def cron_update_stage_id_from_state(self):
        """ Cron: Sync stage_id with state based on stage.code """
        stage_map = {s.code: s.id for s in self.env['stock.picking.stage'].search([])}
        pickings = self.search([('state', '!=', False)])

        for picking in pickings:
            if picking.state in stage_map:
                picking.write({'stage_id': stage_map[picking.state]})



class StockPickingStage(models.Model):
    _name = 'stock.picking.stage'
    _description = 'Delivery Stages'
    _order = 'sequence'

    name = fields.Char(required=True)
    code = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting'),
        ('confirmed', 'Confirmed'),
        ('assigned', 'Assigned'),
        ('pick_pack', 'Pick Pack'),
        ('ready_for_pickup', 'Ready For Pickup'),
        ('picked_up_by_logistic', 'Picked Up By Logistic'),
        ('pickup_by_buyer', 'Pickup By Buyer'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], required=True)
    sequence = fields.Integer(default=10)

    @api.model
    def cron_create_default_stages(self):
        """Create all default delivery stages if not exist"""
        default_stages = [
            ('draft', 'Draft'),
            ('waiting', 'Waiting'),
            ('confirmed', 'Confirmed'),
            ('assigned', 'Assigned'),
            ('pick_pack', 'Pick Pack'),
            ('ready_for_pickup', 'Ready For Pickup'),
            ('picked_up_by_logistic', 'Picked Up By Logistic'),
            ('pickup_by_buyer', 'Pickup By Buyer'),
            ('in_transit', 'In Transit'),
            ('delivered', 'Delivered'),
            ('done', 'Done'),
            ('cancel', 'Cancelled'),
        ]

        for sequence, (code, name) in enumerate(default_stages, start=1):
            stage = self.search([('code', '=', code)], limit=1)
            if not stage:
                self.create({
                    'name': name,
                    'code': code,
                    'sequence': sequence,
                })
            else:
                stage.write({
                    'name': name,
                    'sequence': sequence
                })
