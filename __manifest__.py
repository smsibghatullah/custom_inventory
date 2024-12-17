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

    'depends': ['base','stock','sale','purchase','account'],

    'data': [
        'views/brand_view.xml',
        'views/invoice_view.xml',
        'views/purchase_order_view.xml',
        'views/sale_order_view.xml',
        'views/sku_master_view.xml',
        'views/templates.xml',
        'security/ir.model.access.csv',
    ],

    'demo': [
        'demo/demo.xml',
    ],

    'installable': True,
    'application': False,
    'auto_install': False,
}
