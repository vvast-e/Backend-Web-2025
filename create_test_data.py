#!/usr/bin/env python
"""
Скрипт для создания тестовых данных
"""
import os
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cometapp.settings')
django.setup()

from services.models import Comet

def create_test_comets():
    """Создание тестовых комет"""
    comets_data = [
        {
            'name': 'Комета Галлея',
            'description': 'Краткопериодическая комета семейства Юпитера. Орбитальный период около 75-76 лет. Известна регулярными появлениями и является одной из самых изученных комет.',
            'price': 1500,  # 15000 / 10
            'k_x': 1.234,
            'k_y': -0.567,
            'k_z': 0.890,
            'image_key': 'halley.jpg'
        },
        {
            'name': 'Комета Хейла-Боппа',
            'description': 'Большая комета, наблюдавшаяся с Земли в 1997 году. Одна из самых ярких комет XX века. Стала одной из самых фотографируемых комет в истории.',
            'price': 2500,  # 25000 / 10
            'k_x': -2.145,
            'k_y': 1.678,
            'k_z': -0.432,
            'image_key': 'hale-bopp.jpg'
        },
        {
            'name': 'Комета NEOWISE',
            'description': 'Комета C/2020 F3, открытая в марте 2020 года телескопом NEOWISE. Хорошо наблюдаемая в 2020 году, вызвала большой интерес среди астрономов-любителей.',
            'price': 1800,  # 18000 / 10
            'k_x': 0.987,
            'k_y': -1.234,
            'k_z': 0.567,
            'image_key': 'neowise.jpg'
        },
        {
            'name': 'Комета Энке',
            'description': 'Краткопериодическая комета с орбитальным периодом около 3.3 лет. Открыта в 1786 году. Одна из самых активных короткопериодических комет.',
            'price': 1200,  # 12000 / 10
            'k_x': -0.876,
            'k_y': 0.543,
            'k_z': -1.098,
            'image_key': None  # Для этой кометы пока нет фото
        },
        {
            'name': 'Комета Темпеля 1',
            'description': 'Краткопериодическая комета, которая была целью миссии Deep Impact в 2005 году. Исследование показало сложную структуру ядра кометы.',
            'price': 2200,  # 22000 / 10
            'k_x': 1.567,
            'k_y': -0.890,
            'k_z': 0.123,
            'image_key': None  # Для этой кометы пока нет фото
        },
        {
            'name': 'Комета 67P/Чурюмова-Герасименко',
            'description': 'Комета, которая была целью миссии Rosetta Европейского космического агентства. Посадочный модуль Philae впервые в истории приземлился на поверхность кометы.',
            'price': 3000,  # 30000 / 10
            'k_x': -0.345,
            'k_y': 1.789,
            'k_z': -0.654,
            'image_key': '67p.jpg'
        }
    ]

    updated_count = 0
    for comet_data in comets_data:
        comet, created = Comet.objects.get_or_create(
            name=comet_data['name'],
            defaults=comet_data
        )
        if created:
            print(f"+ Создана комета: {comet.name}")
        else:
            # Обновляем существующие данные
            for key, value in comet_data.items():
                if key != 'name':  # name не обновляем, так как это ключ
                    setattr(comet, key, value)
            comet.save()
            updated_count += 1
            print(f"~ Обновлена комета: {comet.name}")

    print(f"\nВсего создано комет: {len(comets_data) - updated_count}")
    print(f"Всего обновлено комет: {updated_count}")
    print(f"Общее количество комет в базе: {Comet.objects.count()}")

if __name__ == '__main__':
    create_test_comets()
