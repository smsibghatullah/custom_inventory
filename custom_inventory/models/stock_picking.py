from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    state = fields.Selection([
        ('draft', 'Draft'),
        ('pick_pack', 'Pick & Pack'),
        ('ready_for_pickup', 'Ready for Pickup'),
        ('picked_up_by_logistic', 'Picked Up by Logistic Car'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('pickup_by_buyer', 'Pickup by Buyer'),
        ('cancel', 'Cancelled'),
    ], string='Status', compute='_compute_state',
        copy=False, index=True, readonly=True, store=True, tracking=True,
        help=" * Draft: The transfer is not confirmed yet.\n"
             " * Pick & Pack: The transfer is in the picking process.\n"
             " * Ready for Pickup: The transfer is ready for pickup.\n"
             " * Picked Up by Logistic Car: The transfer has been picked up by the logistics car.\n"
             " * In Transit: The transfer is on the way to the delivery location.\n"
             " * Delivered: The transfer has been delivered.\n"
             " * Pickup by Buyer: The buyer picked up the transfer.\n"
             " * Cancelled: The transfer has been cancelled.")

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
