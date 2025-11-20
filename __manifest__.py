# -*- coding: utf-8 -*-
{
    'name': 'POS Referral System',
    'summary': 'Referral system with conditional code generation',

    'description': """
Long description of module's purpose
    """,

    'author': "Mubeen Bahuu",
    'website': "https://www.zavior.org",

    'category': 'Point of Sale',
    'version': '18.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['base','point_of_sale', 'contacts'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/pos_order_views.xml',
        'views/referral_code_views.xml',
        'views/referral_settings_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_referral_system/static/src/css/referral_popup.css',
            'pos_referral_system/static/src/js/ReferralSystem.js',
            'pos_referral_system/static/src/xml/ControlButtons.xml',
            'pos_referral_system/static/src/xml/ReferralPopup.xml',
            'pos_referral_system/static/src/xml/ReceiptScreen.xml'
        ],
    },
}

