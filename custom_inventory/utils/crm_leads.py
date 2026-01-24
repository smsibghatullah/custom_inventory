from markupsafe import Markup


def log_to_crm_history(subject, body_message, sale_order, copy_history_records=False):
    """
    Generic method to post a message to the associated CRM Lead's chatter.

    :param subject: The subject line for the message.
    :param body_message: The main message body (can contain HTML).
    :param related_record: The record that triggered the event (e.g., the sale order).
    """

    env = sale_order.env
    # Ensure we have a link to the CRM lead via the related record
    opportunity_id = sale_order.opportunity_id 

    if opportunity_id:
        if copy_history_records:
            messages = env['mail.message'].search([
                ('res_id', '=', sale_order.id),
                ('model', '=', 'sale.order')
            ])
            for message in messages:
                message.copy({
                    'res_id': opportunity_id.id,
                    'model': 'crm.lead',
                    'subject': f"History from SO #{sale_order.name}: {message.subject or ''}"
                })
            
        opportunity_id.message_post(
            body=Markup(body_message),
            subject=subject,
            subtype_xmlid='mail.mt_note'
        )

        return True
    return False