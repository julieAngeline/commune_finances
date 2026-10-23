{
    'name': 'Commune Finances',
    'version': '17.0.1.0.0',

    'summary': 'Pilotage intelligent des ressources financières disponibles '
               'à la Commune Urbaine de Fianarantsoa',

    'description': '''
        Gestion des recettes, dépenses et calcul automatique
        du Fonds Libre pour la Commune Urbaine de Fianarantsoa.

        Inclut :
        - Exercices budgétaires avec états automatiques
        - Recettes / Dépenses / Budgets
        - Dashboard financier
        - Assistant IA conversationnel (chatbot) basé sur Ollama
    ''',

    'category': 'Accounting/Accounting',
    'author': 'Julie',
    'maintainer': 'Julie',
    'license': 'LGPL-3',
    'sequence': 10,

    'depends': [
        'base',
        'mail',
        'web',          # nécessaire pour les assets JS / dashboard
    ],

    'external_dependencies': {
        'python': ['requests'],   # utilisé par models/chatBot.py
    },

    'data': [
        # Sécurité
        'security/commune_finances_security.xml',
        'security/ir.model.access.csv',

        # Vues métier
        'views/exercice_views.xml',
        'views/recette_views.xml',
        'views/budget_depense_views.xml',
        'views/budget_recette_views.xml',
        'views/depense_views.xml',
        'views/dashboard_views.xml',

        # Chatbot
        'views/chatbot_views.xml',

        # Données / crons
        'data/cron.xml',
    ],

    'assets': {
        'web.assets_backend': [
            # Décommente si tu as des assets JS/CSS pour le dashboard
            # 'commune_finances/static/src/js/**/*.js',
            # 'commune_finances/static/src/scss/**/*.scss',
        ],
    },

    'installable': True,
    'application': True,
    'auto_install': False,
}