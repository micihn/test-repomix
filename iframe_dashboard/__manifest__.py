{
    'name': 'IFrame Dashboard',
    'version': '1.0',
    'category': 'Extra Tools',
    'summary': 'Set up iframe dashboards with custom URLs',
    'description': """
        This module allows administrators to set up iframe dashboards by specifying URLs.
        Users can access these dashboard views through iframes.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base'],
    'data': [
        'security/iframe_dashboard_security.xml',
        'security/ir.model.access.csv',
        'views/iframe_dashboard_views.xml',
        'views/iframe_dashboard_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}