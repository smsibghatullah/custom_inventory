# -*- coding: utf-8 -*-

import logging
import re
from urllib.parse import urlencode

from markupsafe import Markup

from odoo import api, models
from odoo.tools import html_escape, html2plaintext

_logger = logging.getLogger(__name__)


class MirChatterMentionNotifier(models.AbstractModel):
    _name = "mir.chatter.mention.notifier"
    _description = "MIR Chatter Mention Notifier"

    def _get_config_bool(self, key, default=True):
        value = self.env["ir.config_parameter"].sudo().get_param(key)

        if value in (False, None, ""):
            return default

        return str(value).lower() in ("1", "true", "yes", "y", "on")

    def _extract_mentioned_partner_ids(self, message):
        """Extract partners mentioned in a chatter message."""

        partner_ids = set()

        for partner in message.partner_ids:
            if partner and partner.id:
                partner_ids.add(partner.id)

        body = message.body or ""

        regex_patterns = [
            r'data-oe-model=[\'"]res\.partner[\'"][^>]*data-oe-id=[\'"](\d+)[\'"]',
            r'data-oe-id=[\'"](\d+)[\'"][^>]*data-oe-model=[\'"]res\.partner[\'"]',
            r'data-mention-model=[\'"]res\.partner[\'"][^>]*data-mention-id=[\'"](\d+)[\'"]',
            r'data-mention-id=[\'"](\d+)[\'"][^>]*data-mention-model=[\'"]res\.partner[\'"]',
        ]

        for pattern in regex_patterns:
            for match in re.findall(pattern, body):
                try:
                    partner_ids.add(int(match))
                except Exception:
                    continue

        return list(partner_ids)

    def _get_record_url(self, message):
        if not message.model or not message.res_id:
            return ""

        base_url = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("web.base.url")
            or ""
        )

        fragment = urlencode({
            "id": message.res_id,
            "model": message.model,
            "view_type": "form",
        })

        return "%s/web#%s" % (base_url.rstrip("/"), fragment)

    def _get_record_display_name(self, message):
        if not message.model or not message.res_id:
            return "Record"

        try:
            record = self.env[message.model].sudo().browse(message.res_id).exists()

            if record:
                return record.display_name
        except Exception:
            pass

        return "%s,%s" % (message.model, message.res_id)

    def _get_model_description(self, message):
        if not message.model:
            return ""

        model = self.env["ir.model"].sudo().search([
            ("model", "=", message.model),
        ], limit=1)

        return model.name or message.model

    def _remove_mention_links_from_body(self, body):
        """Remove @mention anchors from chatter body before converting to text."""

        if not body:
            return ""

        cleaned = body

        mention_anchor_patterns = [
            r'<a[^>]*data-oe-model=[\'"]res\.partner[\'"][^>]*>.*?</a>',
            r'<a[^>]*data-mention-model=[\'"]res\.partner[\'"][^>]*>.*?</a>',
            r'<a[^>]*href=[\'"][^\'"]*model=res\.partner[^\'"]*[\'"][^>]*>.*?</a>',
        ]

        for pattern in mention_anchor_patterns:
            cleaned = re.sub(
                pattern,
                "",
                cleaned,
                flags=re.IGNORECASE | re.DOTALL,
            )

        return cleaned

    def _clean_plain_message_text(self, text):
        """Remove html2plaintext footnotes and leftover mention text."""

        if not text:
            return ""

        cleaned = text.strip()

        # Remove footnote lines:
        # [1] http://localhost:8024/web#model=res.partner&id=15
        cleaned = re.sub(
            r'^\s*\[\d+\]\s+https?://.*$',
            "",
            cleaned,
            flags=re.MULTILINE,
        )

        # Remove inline footnote markers like [1]
        cleaned = re.sub(r'\s*\[\d+\]', "", cleaned)

        # Remove extra blank lines
        cleaned = re.sub(r'\n\s*\n+', "\n", cleaned)

        return cleaned.strip()

    def _get_original_message_text(self, message):
        """Return chatter body as clean plain text without @mention links."""

        body_without_mentions = self._remove_mention_links_from_body(
            message.body or ""
        )

        text = html2plaintext(body_without_mentions)

        return self._clean_plain_message_text(text)

    def _get_or_create_direct_channel(self, author_partner, target_partner):
        Channel = self.env["discuss.channel"].sudo()

        channel = Channel.search([
            ("channel_type", "=", "chat"),
            ("channel_partner_ids", "in", [author_partner.id]),
            ("channel_partner_ids", "in", [target_partner.id]),
        ], limit=1)

        if channel:
            return channel

        return Channel.create({
            "name": "Chat between %s and %s" % (
                author_partner.display_name,
                target_partner.display_name,
            ),
            "channel_type": "chat",
            "channel_partner_ids": [
                (4, author_partner.id),
                (4, target_partner.id),
            ],
        })

    def _build_discuss_body(self, message):
        """Build HTML Discuss body.

        The record URL is hidden behind a clickable button/link.
        The raw URL will not be shown in the message body.
        """

        author_name = message.author_id.display_name or self.env.user.display_name
        record_name = self._get_record_display_name(message)
        model_name = self._get_model_description(message)
        record_url = self._get_record_url(message)
        original_text = self._get_original_message_text(message)

        button_html = ""

        if record_url:
            button_html = """
                <br/>
                <a href="%s" target="_blank"
                   style="background:#875A7B;
                          color:black;
                          padding:8px 12px;
                          text-decoration:none;
                          border-radius:6px;
                          display:inline-block;
                          margin-top:8px;">
                    👉 Open Record
                </a>
            """ % html_escape(record_url)

        message_html = """
            <div>
                <b>🔔 You were mentioned</b><br/>
                <b>By:</b> %s<br/>
                <b>Model:</b> %s<br/>
                <b>Record:</b> %s<br/>
                <b>Record ID:</b> %s<br/>
                %s
        """ % (
            html_escape(author_name),
            html_escape(model_name),
            html_escape(record_name),
            html_escape(str(message.res_id or "")),
            button_html,
        )

        if original_text:
            message_html += """
                <br/><br/>
                <b>Message:</b><br/>
                <div style="border-left:3px solid #dddddd;
                            padding-left:10px;
                            margin-top:6px;">
                    %s
                </div>
            """ % html_escape(original_text)

        message_html += """
            </div>
        """

        return Markup(message_html)

    def _build_email_body(self, message):
        """Clean email body.

        Record name is clickable in email.
        URL is not shown separately.
        Original chatter mention links are removed.
        """

        author_name = message.author_id.display_name or self.env.user.display_name
        record_name = self._get_record_display_name(message)
        model_name = self._get_model_description(message)
        record_url = self._get_record_url(message)
        original_text = self._get_original_message_text(message)

        if record_url:
            record_html = (
                '<a href="%s" '
                'style="color:#714B67; font-weight:bold; text-decoration:none;">'
                "%s</a>"
            ) % (
                html_escape(record_url),
                html_escape(record_name),
            )
        else:
            record_html = "<strong>%s</strong>" % html_escape(record_name)

        body = """
            <div style="font-family: Arial, sans-serif; font-size: 14px; color: #222;">
                <p>
                    <strong>%s</strong> mentioned you on
                    <strong>%s</strong>.
                </p>

                <table style="border-collapse: collapse; margin-top: 10px;">
                    <tr>
                        <td style="padding: 4px 10px 4px 0; color: #666;">Record</td>
                        <td style="padding: 4px 0;">%s</td>
                    </tr>
                    <tr>
                        <td style="padding: 4px 10px 4px 0; color: #666;">Record ID</td>
                        <td style="padding: 4px 0;">%s</td>
                    </tr>
                </table>
        """ % (
            html_escape(author_name),
            html_escape(model_name),
            record_html,
            html_escape(str(message.res_id or "")),
        )

        if original_text:
            body += """
                <p style="margin-top: 18px; color: #666;">Message:</p>
                <div style="white-space: pre-line; border-left: 3px solid #ddd; padding-left: 10px;">
                    %s
                </div>
            """ % html_escape(original_text)

        body += "</div>"

        return body

    def _send_discuss_message(self, message, target_partner):
        author_partner = message.author_id or self.env.user.partner_id

        if not author_partner or not target_partner:
            return

        channel = self._get_or_create_direct_channel(author_partner, target_partner)
        body = self._build_discuss_body(message)

        channel.with_context(mir_mention_notify_skip=True).message_post(
            body=body,
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            author_id=author_partner.id,
        )

    def _send_email_message(self, message, target_partner):
        if not target_partner.email:
            return

        author_partner = message.author_id or self.env.user.partner_id
        record_name = self._get_record_display_name(message)
        model_name = self._get_model_description(message)

        subject = "You were mentioned on %s: %s [ID: %s]" % (
            model_name,
            record_name,
            message.res_id or "",
        )

        body_html = self._build_email_body(message)

        email_from = False

        if author_partner and author_partner.email:
            email_from = author_partner.email_formatted or author_partner.email

        mail_values = {
            "subject": subject,
            "body_html": body_html,
            "email_to": target_partner.email,
            "auto_delete": False,
        }

        if email_from:
            mail_values["email_from"] = email_from

        mail = self.env["mail.mail"].sudo().with_context(
            mir_mention_notify_skip=True
        ).create(mail_values)

        mail.sudo().with_context(mir_mention_notify_skip=True).send()

    def _notify_message_mentions(self, message):
        """Send Discuss and Email notifications for chatter mentions."""

        if message.model == "discuss.channel":
            return

        if not message.model or not message.res_id:
            return

        if not message.body:
            return

        if message.message_type not in ("comment", "notification", "email"):
            return

        mentioned_partner_ids = self._extract_mentioned_partner_ids(message)

        if not mentioned_partner_ids:
            return

        send_discuss = self._get_config_bool(
            "mir_chatter_mention_notify.send_discuss",
            default=True,
        )

        send_email = self._get_config_bool(
            "mir_chatter_mention_notify.send_email",
            default=True,
        )

        if not send_discuss and not send_email:
            return

        author_partner = message.author_id or self.env.user.partner_id
        partners = self.env["res.partner"].sudo().browse(mentioned_partner_ids).exists()

        for partner in partners:
            if author_partner and partner.id == author_partner.id:
                continue

            users = self.env["res.users"].sudo().search([
                ("partner_id", "=", partner.id),
                ("active", "=", True),
                ("share", "=", False),
            ], limit=1)

            if not users:
                continue

            if send_discuss:
                self._send_discuss_message(message, partner)

            if send_email:
                self._send_email_message(message, partner)