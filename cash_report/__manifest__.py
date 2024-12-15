{
    'name': 'Cash Account Report',
    'version': '16.0.1.0.0',
    'category': 'Accounting/Reports',
    'summary': 'Detailed Cash Account Report with Running Balance',
    'description': """
        Generate detailed cash account reports with:
        - Running balance calculation
        - Multi-company support
        - Date range selection
        - PDF export capability
    """,
    'depends': ['base', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'report/cash_report_template.xml',
        'report/setoran_report_template.xml',
        'report/setoran_langsung_template.xml',
        'report/employee_rekap_template.xml',
        'wizard/cash_report_wizard_view.xml',
        'wizard/setoran_report_wizard_view.xml',
        'wizard/setoran_langsung_wizard_view.xml',
        'wizard/employee_rekap_wizard_view.xml',
        'views/cash_report_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

