from datetime import date

SERVICES_DATA = [
    {
        'id': 1,
        'name': 'Комета Галлея',
        'price': 1200,
        'event_date': date(2061, 7, 28),
        'description': 'Расчёт гелиоцентрического расстояния по текущим сферическим координатам кометы Галлея. Включает оценку погрешности и ссылку на эфемериды JPL.',
        'image_key': 'halley.jpg',
    },
    {
        'id': 2,
        'name': 'Комета C/1995 O1 (Хейла — Боппа)',
        'price': 1800,
        'event_date': date(1997, 3, 22),
        'description': 'Высокоточная реконструкция расстояния от Солнца по координатам и параметрам орбиты, архивные данные наблюдений 1995–1997 гг.',
        'image_key': 'hale-bopp.jpg',
    },
    {
        'id': 3,
        'name': 'Комета 67P/Чурюмова — Герасименко',
        'price': 1500,
        'event_date': date(2021, 11, 2),
        'description': 'Расчёт в эпохе миссии Rosetta, сопоставление с данными NAVCAM. Гарантированная повторяемость результата.',
        'image_key': '67p.jpg',
    },
    {
        'id': 4,
        'name': 'Комета C/2020 F3 (NEOWISE)',
        'price': 1600,
        'event_date': date(2020, 7, 23),
        'description': 'Расстояние от Солнца вблизи перигелия по наблюдательным координатам, визуализация с хвостом пыли и газа.',
        'image_key': 'neowise.jpg',
    },
]

ORDERS_DATA = {
    1: {
        'id': 1,
        'items': [
            {'service_id': 1, 'quantity': 1, 'sort_order': 1, 'is_main': True},
            {'service_id': 3, 'quantity': 1, 'sort_order': 2, 'is_main': False},
        ]
    }
}

def get_minio_url(image_key):
    """Построение URL изображения в MinIO"""
    return f"http://localhost:9000/comets/{image_key}"

