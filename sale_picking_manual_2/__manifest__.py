# -*- coding: utf-8 -*-
# Part of Kiran Infosoft. See LICENSE file for full copyright and licensing details.
{
    'name': "Create delivery order manually from sale order",
    'summary': "Create delivery order manually from sale order",
    'description': """
Module allow to Create delivery order manually from sale order
===============================================================
Manual Delivery Order
Manual Picking
Delivery Order
Sale Order
""",
    "version": "1.0",
    "category": "Sales",
    'price': 25.0,
    'currency': 'EUR',
    'author': "Kiran Infosoft",
    "website": "http://www.kiraninfosoft.com",
    'license': 'Other proprietary',
    'images': ['static/description/logo.png'],
    "depends": [
        'sale_stock'
    ],
    "data": [
        'wizards/create_picking_wizard.xml',
        'views/sale_view.xml'
    ],
    "application": False,
    'installable': True,
}
