# -*- coding: utf-8 -*-
# © 2021 ZOLVANT (Agustin Pianciola <agustin@zolvant.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
#account_withholding_automatic
{
    'name': 'Account Journal Position',
    'version': '13.0.1.0.0',
    'category': 'Accounting & Finance',
    'license': 'AGPL-3',
    'summary': 'Configure allwable fiscal positiones on journals',
    'description': """
Account Journal Position
==========================================

Configure allwable fiscal positiones on journals

This module has been written by Agustin Pianciola <agustin@zolvant.com>.
    """,
    'author': "ZOLVANT",
    'website': 'http://www.zolvant.com',
    'depends': ['account', 'account_payment', 'account_payment_group', 'purchase', 'sale', 'account_payment_fix','account_withholding_automatic','purchase_stock'],
    'data': [
        'account_fiscal_position_view.xml',
        'account_payment_group_view.xml',
    ],
    'installable': True,
}