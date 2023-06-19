{
    'name': 'NU Event Organizer',
    'version': '16.0.1.0.0',
    'author': 'BSCS',
    'website': 'http://www.edu.pk',
    'category': 'Event Management System',
    'license': "AGPL-3",
    'Summary': 'A Module For Event Management System',
    'images': ['./static/description/icon.png'],
    'depends': ['base','account'],
    'data': ['views/nu_event_test_view.xml', 'views/nu_event_test_menu.xml', 'views/nu_participant_state.xml'],

    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    # 'post_init_hook': '_method_run_before_installation',
}