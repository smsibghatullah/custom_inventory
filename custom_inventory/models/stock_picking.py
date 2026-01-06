from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting'),
        ('assigned', 'Ready'),
        ('pick_pack', 'Pick & Pack'),
        ('ready_for_pickup', 'Ready for Pickup'),
        ('picked_up_by_logistic', 'Picked Up by Logistic Car'),
        ('pickup_by_buyer', 'Pickup by Buyer'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', compute='_compute_state',group_expand='_read_group_state_ids',
        copy=False, index=True, readonly=True, store=True, tracking=True,
        help=" * Draft: The transfer is not confirmed yet.\n"
             " * Pick & Pack: The transfer is in the picking process.\n"
             " * Ready for Pickup: The transfer is ready for pickup.\n"
             " * Picked Up by Logistic Car: The transfer has been picked up by the logistics car.\n"
             " * In Transit: The transfer is on the way to the delivery location.\n"
             " * Delivered: The transfer has been delivered.\n"
             " * Pickup by Buyer: The buyer picked up the transfer.\n"
             " * Cancelled: The transfer has been cancelled.")
    courier_fields = fields.Boolean(string="Courier Fields", compute="_compute_carrier_fields")
    standard_delivery_fields = fields.Boolean(string="Standard Delivery Fields", compute="_compute_carrier_fields")
    readonly_fields = fields.Boolean(string="Readonly Fields", compute="_compute_field_readonly")
    courier_and_standard_fields = fields.Boolean(string="Both Fields", compute="_compute_carrier_fields")
    show_statusbar = fields.Boolean(compute="_compute_show_statusbar")

    @api.model
    def _read_group_state_ids(self, states, domain, orderby=''):
        """Ensure all states are shown as Kanban columns, even if empty."""
        return [key for key, _ in self.fields_get(allfields=['state'])['state']['selection']]

    def button_validate(self):
        skip_journal = self.env.context.get("skip_journal")
        if not skip_journal:
            for picking in self:
                if picking.sale_id:
                    picking.sale_id.create_journal_entry()
                elif picking.purchase_id:
                    picking.purchase_id.create_journal_entry()

        res = super(StockPicking, self).button_validate()
        return res

    @api.depends('sale_id')
    def _compute_show_statusbar(self):
        for record in self:
            record.show_statusbar = bool(record.sale_id)  

    @api.onchange('carrier_id')
    def _compute_carrier_fields(self):
        for record in self:
            print("oooooooooooooooooooooooooooooooooooooooooooooooo")
            if record.carrier_id and record.sale_id:
                record.courier_fields = record.carrier_id.code == 'courier'
                record.standard_delivery_fields = record.carrier_id.code == 'standard_delivery'
                record.courier_and_standard_fields = record.carrier_id.code == 'courier' or record.carrier_id.code == 'standard_delivery'
                print(record.courier_fields,"kkkkkkkkkkkkkkkkkkkkkkk",record.standard_delivery_fields)
            else:
                record.courier_fields = False
                record.standard_delivery_fields = False
                record.courier_and_standard_fields = False
                
            if record.carrier_id.code == 'courier' and record.state in ['in_transit','picked_up_by_logistic','delivered','done','cancel']:
                record.readonly_fields = True
            elif record.carrier_id.code == 'standard_delivery' and record.state in ['done', 'pickup_by_buyer','cancel']:
                record.readonly_fields = True
            else:
                record.readonly_fields = False

    @api.depends('state')
    def _compute_field_readonly(self):
        for record in self:
            if record.carrier_id.code == 'courier' and record.state in ['in_transit','picked_up_by_logistic','delivered','done','cancel']:
                record.readonly_fields = True
            elif record.carrier_id.code == 'standard_delivery' and record.state in ['done', 'pickup_by_buyer','cancel']:
                record.readonly_fields = True
            else:
                record.readonly_fields = False

    def action_pick_pack(self):
        for record in self:
            record.state = 'pick_pack'

    def action_ready_for_pickup(self):
        for record in self:
            record.state = 'ready_for_pickup'

    def action_picked_up_by_logistic(self):
        for record in self:
            record.state = 'picked_up_by_logistic'

    def action_in_transit(self):
        for record in self:
            record.state = 'in_transit'

    def action_delivered(self):
        for record in self:
            record.state = 'delivered'

    def action_pickup_by_buyer(self):
        for record in self:
            record.state = 'pickup_by_buyer'
        

class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    code = fields.Char(string="Code", help="Enter the unique code for the delivery carrier.")
