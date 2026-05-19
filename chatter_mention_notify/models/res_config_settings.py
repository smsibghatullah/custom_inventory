# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    mir_chatter_mention_notify_discuss = fields.Boolean(
        string="Send Discuss message on chatter mention",
        config_parameter="mir_chatter_mention_notify.send_discuss",
        default=True,
    )

    mir_chatter_mention_notify_email = fields.Boolean(
        string="Send email on chatter mention",
        config_parameter="mir_chatter_mention_notify.send_email",
        default=True,
    )
