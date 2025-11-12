CONFIG = {
    'contracts': {
        'Zero Zero Seven': ['Cairo', 'Assiut', 'Hurghada', 'Minya', 'Port Said', 'Mansoura', 'Damanhour', 'Al Mahallah Al Kubra', 'Alexandria']
    },
    'cities': [
        'Cairo',
        'Assiut',
        'Hurghada',
        'Minya',
        'Port Said',
        'Mansoura',
        'Damanhour',
        'Al Mahallah Al Kubra',
        'Alexandria'
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