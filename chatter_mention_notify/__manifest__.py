# -*- coding: utf-8 -*-
{
    "name": "Chatter Mention Notify",
    "version": "17.0.1.0.0",
    "category": "Discuss",
    "summary": "Send Discuss and Email notification when a user is mentioned in any chatter message",
    "description": """
When a user is tagged/mentioned in chatter on any model, this module sends:
1) Private Discuss chat message
2) Email notification

It works globally through mail.message, so no per-model button code is required.
""",
    "author": "",
    "depends": [
        "base",
        "mail",
    ],
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
