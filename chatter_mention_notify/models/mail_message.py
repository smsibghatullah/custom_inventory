# -*- coding: utf-8 -*-

import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class MailMessage(models.Model):
    _inherit = "mail.message"

    @api.model_create_multi
    def create(self, vals_list):
        messages = super().create(vals_list)

        if self.env.context.get("mir_mention_notify_skip"):
            return messages

        notifier = self.env["mir.chatter.mention.notifier"].sudo()

        for message in messages:
            try:
                notifier._notify_message_mentions(message)
            except Exception:
                _logger.exception(
                    "MIR chatter mention notify failed for mail.message id %s",
                    message.id,
                )

        return messages
