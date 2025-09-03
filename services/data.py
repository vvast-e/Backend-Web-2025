from datetime import date
from math import pi, sin, cos

# Гауссова гравитационная постоянная (астрономические единицы, дни)
GAUSSIAN_K = 0.01720209895

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


# Орбитальные элементы (упрощённые, эллиптические) для оценки гелиоцентрического расстояния r
# Формат: a (AU), e, tp (дата прохождения перигелия)
ORBITAL_ELEMENTS = {
    # Комета Галлея — следующий перигелий ожидается 2061-07-28
    'halley.jpg': {
        'a': 17.834, 'e': 0.96714, 'tp': date(2061, 7, 28)
    },
    # Хейла — Боппа — перигелий около 1997-04-01
    'hale-bopp.jpg': {
        'a': 186.0, 'e': 0.9951, 'tp': date(1997, 4, 1)
    },
    # 67P/Чурюмова — Герасименко — перигелий 2021-11-02
    '67p.jpg': {
        'a': 3.463, 'e': 0.640, 'tp': date(2021, 11, 2)
    },
    # C/2020 F3 (NEOWISE) — перигелий 2020-07-03
    'neowise.jpg': {
        'a': 266.0, 'e': 0.99921, 'tp': date(2020, 7, 3)
    },
}


def _solve_kepler_equation(mean_anomaly: float, eccentricity: float) -> float:
    """Решение уравнения Кеплера для эллиптической орбиты.
    Возвращает эксцентриситетную аномалию E (радианы).
    """
    M = mean_anomaly % (2 * pi)
    e = eccentricity
    # Начальное приближение
    E = M if e < 0.8 else pi
    for _ in range(50):
        f = E - e * sin(E) - M
        fp = 1 - e * cos(E)
        d = f / fp
        E -= d
        if abs(d) < 1e-10:
            break
    return E


def calculate_heliocentric_distance_au(image_key: str, on_date: date) -> float:
    """Оценка гелиоцентрического расстояния r в а.е. по упрощённым орбитальным элементам.
    Используется эллиптическая модель: r = a * (1 - e * cos(E)),
    где E находится решением уравнения Кеплера M = E - e sin(E),
    M = n * (t - tp), n = k / a^{3/2}.
    """
    el = ORBITAL_ELEMENTS.get(image_key)
    if not el:
        return float('nan')
    a = el['a']
    e = el['e']
    tp = el['tp']
    dt_days = (on_date - tp).days
    n = GAUSSIAN_K / (a ** 1.5)
    M = n * dt_days
    E = _solve_kepler_equation(M, e)
    r = a * (1 - e * cos(E))
    return r

