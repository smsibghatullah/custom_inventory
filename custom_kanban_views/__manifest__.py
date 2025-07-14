# -*- coding: utf-8 -*-
{
    'name': "Custom Kanban Views",

    'summary': "Enhanced kanban views with progress bars and stage-wise record insights.",

    'description': """
This module enhances the kanban view functionality by adding additional progress bars, 
including record count and revenue summaries for CRM and related models.
    """,

    'author': "Dynamic Solution Makers",
    'website': "https://www.dsmpk.com",

    'category': 'Customization',
    'version': '1.0',

    'depends': [
        'base',
        'stock',
        'sale',
        'purchase',
        'account',
        'purchase_stock',
        'crm',
        'sale_crm',
        'delivery',
        'project',
        'survey',
        'product',
        'maintenance',
        'hr_maintenance',
        'gsk_automatic_mail_server',
        'hide_menu_user',
        'hr_attendance',
        'custom_inventory'
    ],

    'data': [
        'security/ir.model.access.csv',
        'data/cron.xml',
        'views/sale_order_kanban_views.xml',
        'views/purchase_order_kanban_views.xml',
        'views/invoice_kanban_views.xml',
        'views/delivery_kanban_view.xml',
        'views/templates.xml',
        'views/delivery_view.xml',
        'views/sale_order_view.xml'
    ],

    'assets': {
        'web.assets_backend': [
            'custom_kanban_views/static/src/xml/crm_template.xml', 
            'custom_kanban_views/static/src/xml/sale_template.xml',  
            'custom_kanban_views/static/src/js/sale_kanban_group_order.js',
            'custom_kanban_views/static/src/js/stock_picking_kanban.js',
        ],
    },

    'demo': [
        'demo/demo.xml',
    ],

    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
