{
    'name': 'Commune Finances',
    'version': '17.0.1.0.0',

    'summary': 'Pilotage intelligent des ressources financières disponibles à la Commune Urbaine de Fianarantsoa',

    'description': '''
        Gestion des recettes, dépenses et calcul automatique
        du Fonds Libre pour la Commune Urbaine de Fianarantsoa.
    ''',

    'category': 'Accounting',
    'author': 'Julie',
    'license': 'LGPL-3',

    'depends': [
        'base',
        'mail',
    ],

    'data': [
        'security/commune_finances_security.xml',
        'security/ir.model.access.csv',

        'views/dashboard_views.xml',
        'views/exercice_views.xml',
        'views/compte_depense_views.xml',
        'views/budget_depense_views.xml',
        'views/recette_views.xml',
        'views/depense_views.xml',
    ],

    'assets': {
        'web.assets_frontend': [
            'commune_finances/static/src/css/login.css',
        ],
        

    },

    'installable': True,
    'application': True,
}