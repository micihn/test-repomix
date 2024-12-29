{
    'name': 'Advanced Inter-Company Transactions',
    'version': '16.0.1.0.0',
    'category': 'Sales/Purchase',
    'summary': 'Manage inter-company sales, purchases and inventory movements with approval workflow',
    'description': """
        This module enables advanced inter-company transactions:
        * Automatic creation of corresponding SO/PO between companies
        * Synchronized inventory movements
        * Optional approval workflow for better control
        * Notes/terms synchronization between documents
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'sale_management',
        'purchase',
        'stock',
        'account',
        'mail',
    ],
    'data': [
        'security/inter_company_security.xml',
        'security/ir.model.access.csv',
        'data/inter_company_data.xml',
        'data/mail_template_data.xml',
        'wizard/inter_company_approve_wizard_views.xml',
        'views/res_config_settings_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/stock_picking_views.xml',
        'views/res_company_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}