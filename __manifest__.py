{
    'name': 'Commune Finances',
    'version': '17.0.1.0.0',
    'summary': 'Pilotage intelligent des ressources financières disponibles à la CUF',
    'description': 'Gestion des recettes, dépenses et calcul automatique du Fonds Libre pour la Commune Urbaine de Fianarantsoa',
    'category': 'Accounting',
    'author': 'Julie',
    'license': 'LGPL-3',
    'depends': [
    'base',
    'mail',
],
 'data': [
    'security/ir.model.access.csv',
    'views/dashboard_views.xml',
    'views/exercice_views.xml',
    'views/compte_recette_views.xml',
    'views/compte_depense_views.xml',
    'views/budget_depense_views.xml',
    'views/regisseur_views.xml',
    'views/recette_views.xml',
    'views/depense_views.xml',
],
      'assets': {
        'web.assets_frontend': [
            'commune_finances/static/src/css/login.css',
        ],
        'web.assets_backend': [
        'commune_finances/static/src/js/recette_popup.js',
    ],
    },
    'installable': True,
    'application': True,
}
