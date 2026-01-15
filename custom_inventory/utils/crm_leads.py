from markupsafe import Markup


def log_to_crm_history(subject, body_message, related_record):
    """
    Generic method to post a message to the associated CRM Lead's chatter.

    :param subject: The subject line for the message.
    :param body_message: The main message body (can contain HTML).
    :param related_record: The record that triggered the event (e.g., the sale order).
    """
    # Ensure we have a link to the CRM lead via the related record
    opportunity_id = related_record.opportunity_id 

    if opportunity_id:
        opportunity_id.message_post(
            body=Markup(body_message),
            subject=subject,
            subtype_xmlid='mail.mt_note'
        )
        return True
    return False