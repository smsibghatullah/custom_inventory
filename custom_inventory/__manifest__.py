# -*- coding: utf-8 -*-
{
    'name': "Custom Inventory Management",

    'summary': "Manage Brand, SKU Types, and Items in Inventory",

    'description': """
Custom Inventory Module
=======================
This module provides functionality to manage:
- Brand Master
- SKU Type Master
- Item Master

Features:
- Tree and Form views for managing records.
- Integrated into the Inventory module for seamless operations.
    
Developed by DSM (Dynamic Solution Maker). For more details, visit:
[www.dsmpk.com](http://www.dsmpk.com)
    """,

    'author': "DSM (Dynamic Solution Maker)",
    'website': "http://www.dsmpk.com",

    'category': 'Inventory',
    'version': '1.0',

    'depends': ['base','stock','sale','purchase','account','purchase_stock','crm', 'sale_crm','delivery'],

    'data': [
         'data/data.xml',
        'views/brand_view.xml',
        'views/bom_products_view.xml',
        'views/invoice_view.xml',
        'views/purchase_order_view.xml',
        'views/sale_order_view.xml',
        'views/sku_master_view.xml',
        'views/templates.xml',
        'views/crm.xml',
        'views/stock_picking_view.xml',
        'views/expense_cost_wizard_view.xml',
        'security/ir.model.access.csv',
       
    ],

  

    'installable': True,
    'application': False,
    'auto_install': False,
}
