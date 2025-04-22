from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re
import logging

_logger = logging.getLogger(__name__)

class MailMail(models.Model):
    _inherit = 'mail.mail'

    def send(self, auto_commit=False, raise_exception=False):
        for mail in self:
            try:
                emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', mail.email_from or '')
                if not emails:
                    continue

                if not mail.mail_server_id or mail.mail_server_id.smtp_user != emails[0]:
                    mail_server = self.env['ir.mail_server'].sudo().search([('smtp_user', '=', emails[0])], limit=1)
                    # if not mail_server:
                    #     raise ValidationError(_("SMTP configuration missing for email: %s") % emails[0])
                    
                    mail.mail_server_id = mail_server.id  
                    mail.email_from = mail_server.smtp_user
            except Exception as e:
                _logger.error("Error processing mail ID %s: %s", mail.id, str(e))
                if raise_exception:
                    raise

        try:
            return super(MailMail, self).send(auto_commit=auto_commit, raise_exception=raise_exception)
        except Exception as e:
            _logger.error("Error sending mail(s): %s", str(e))
            if raise_exception:
                raise
            return False
