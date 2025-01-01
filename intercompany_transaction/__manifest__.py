{
    'name': 'Inter Company Transactions',
    'version': '16.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Manage transactions between companies',
    'description': """
        This module allows you to manage inter-company transactions with:
        * Synchronization of Sales/Purchase Orders
        * Synchronization of Customer/Vendor Bills
        * Configurable validation workflows
    """,
    'depends': [
        'base',
        'account',
        'sale_management',
        'purchase',
    ],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/account_move_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'data/security_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}