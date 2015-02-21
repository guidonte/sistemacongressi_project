{
    'name': 'Sistema Congressi - Project',
    'description': 'Project settings for Sistema Congressi s.r.l.',
    'author': 'Goodora s.r.l.',
    'version': '0.1',
    'category': 'Hidden',
    'depends': [
        'project',
        'hr',
        'account_budget',
        'analytic',
        'product',
        'purchase',
    ],
    'data': [
        'project_view.xml',
        'res_groups.xml',
        'purchase_view.xml',
        'exports/export_meeting.xml',
    ],
    'installable': True,
    'auto_install': False,
}

