CONFIG = {
    'contracts': {
        'Al Abtal': ['Hurghada', 'Port said'],
        'Al Alamia': ['Ismalia', 'Port said', 'Suez'],
        'Ebad El rahman': ['Hurghada', 'Minya'],
        'El Tohami': ['Assiut', 'Hurghada', 'Minya', 'Suez', 'Beni Suef'],
        'MTA': ['Hurghada', 'Port said'],
        'Stop Car': ['Hurghada', 'Ismalia', 'Port said', 'Suez', 'Beni Suef'],
        'Tanta Car': ['Ismalia', 'Port said', 'Suez'],
        'Tantawy': ['Assiut', 'Hurghada', 'Ismalia', 'Port said', 'Suez'],
        'Team mh for Delivery': ['Hurghada', 'Suez'],
        'Wasaly': ['Assiut'],
        'Zero Zero Seven': ['Assiut', 'Hurghada']
    },
    'cities': [
        'Assiut',
        'Beni Suef',
        'Hurghada',
        'Ismalia',
        'Minya',
        'Port said',
        'Suez'
    ],
    'columns_to_keep': [
        'employee id',
        'shift status',
        'planned start date',
        'planned end date',
        'planned start time',
        'planned end time'
    ],
    'columns_to_remove': [
        'shift id',
        'employee name',
        'starting point id',
        'starting point',
        'shift tag',
        'planned duration',
        'actual start date',
        'actual end date',
        'actual start time',
        'actual end time',
        'actual duration'
    ],
    'shift_status_to_remove': [
        'NO_SHOW(UNEXCUSED)',
        'NO_SHOW_EXCUSED(EXCUSED)'
    ]
} 