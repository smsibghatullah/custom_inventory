# -*- coding: utf-8 -*-
{
    'name': 'Akahu Bank Integration',
    'version': '1.0',
    'summary': 'Integration with Akahu API to sync bank accounts and transactions.',
    'description': """
Akahu Bank Integration
=======================
Synchronize bank account information and transactions from Akahu API into Odoo.

Features:
- Fetch and sync bank accounts
- Store balance, currency, and account status
- Integration with customers (res.partner)
    """,
    'author': 'Dynamic Solution Maker',
    'website': 'https://www.dsmpk.com',
    'category': 'Accounting/Finance',
    'depends': ['base', 'contacts','account','sale'],
    'data': [
        'data/data.xml',
        'security/ir.model.access.csv',
        'views/menu_views.xml',
        'views/akahu_bank_account_views.xml',
        'views/akahu_transaction_views.xml',
        'views/account_journal_dashboard_kanban_view.xml',
        'views/akahu_transaction_link_views.xml',
        'wizard/invoice_wizard_view.xml',
        'wizard/bank_account_wizard_view.xml',
        'wizard/payment_wizard_view.xml',
        'wizard/attachment_wizard_view.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
