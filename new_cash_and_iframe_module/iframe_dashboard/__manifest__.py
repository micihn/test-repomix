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
    'depends': ['base', 'cash_report'],
    'data': [
        'security/iframe_dashboard_security.xml',
        'security/ir.model.access.csv',
        'views/iframe_dashboard_views.xml',  # This creates the action
        'views/iframe_dashboard_menu.xml',   # This creates the root menu
        'views/iframe_dashboard_submenus.xml',  # This creates submenus using the action
        'views/cash_report_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}