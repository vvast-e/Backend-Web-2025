from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from services.models import Comet
from services.data import SERVICES_DATA


COMETS_DATA = [
    {
        'id': 1,
        'name': 'Комета Галлея',
        'description': 'Периодическая комета из семейства Юпитера. Возвращается к Земле каждые 75-76 лет. Последнее появление было в 1986 году, следующее ожидается в 2061 году.',
        'price': 50000,
        'image_key': 'halley.jpg',
        'k_x': 0.587,
        'k_y': 0.349,
        'k_z': -0.124,
    },
    {
        'id': 2,
        'name': 'Комета C/1995 O1 (Хейла — Боппа)',
        'description': 'Одна из самых ярких комет XX века. Была видна невооруженным глазом рекордные 18 месяцев. Период обращения составляет около 2533 лет.',
        'price': 75000,
        'image_key': 'hale-bopp.jpg',
        'k_x': 0.714,
        'k_y': -0.412,
        'k_z': 0.568,
    },
    {
        'id': 3,
        'name': 'Комета C/2020 F3 (NEOWISE)',
        'description': 'Комета C/2020 F3 (NEOWISE), открытая космическим телескопом NEOWISE. Была видна невооруженным глазом в июле 2020 года.',
        'price': 60000,
        'image_key': 'neowise.jpg',
        'k_x': -0.123,
        'k_y': 0.456,
        'k_z': 0.789,
    },
    {
        'id': 4,
        'name': 'Комета 67P/Чурюмова — Герасименко',
        'description': 'Короткопериодическая комета с периодом обращения 6.45 лет. В 2014 году на неё совершил посадку космический аппарат "Розетта".',
        'price': 80000,
        'image_key': '67p.jpg',
        'k_x': 0.234,
        'k_y': 0.567,
        'k_z': -0.345,
    },
]


class Command(BaseCommand):
    help = 'Наполняет базу данных начальными данными о кометах и пользователях'

    def handle(self, *args, **options):
        self.stdout.write('Начинаю наполнение базы данных...')
        
        for comet_data in COMETS_DATA:
            comet, created = Comet.objects.update_or_create(
                id=comet_data['id'],
                defaults={
                    'name': comet_data['name'],
                    'description': comet_data['description'],
                    'price': comet_data['price'],
                    'image_key': comet_data['image_key'],
                    'k_x': comet_data['k_x'],
                    'k_y': comet_data['k_y'],
                    'k_z': comet_data['k_z'],
                    'is_deleted': False,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Создана комета: {comet.name}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Обновлена комета: {comet.name}'))
        
        chief_astronomer, created = User.objects.get_or_create(
            username='chief@example.com',
            defaults={
                'email': 'chief@example.com',
                'is_superuser': True,
                'is_staff': True,
            }
        )
        if created:
            chief_astronomer.set_password('chief123')
            chief_astronomer.save()
            self.stdout.write(self.style.SUCCESS('Создан главный астроном: chief@example.com / chief123'))
        else:
            self.stdout.write(self.style.WARNING('Главный астроном уже существует'))
        
        astronomer, created = User.objects.get_or_create(
            username='astronomer@example.com',
            defaults={
                'email': 'astronomer@example.com',
                'is_superuser': False,
                'is_staff': False,
            }
        )
        if created:
            astronomer.set_password('astro123')
            astronomer.save()
            self.stdout.write(self.style.SUCCESS('Создан астроном: astronomer@example.com / astro123'))
        else:
            self.stdout.write(self.style.WARNING('Астроном уже существует'))
        
        self.stdout.write(self.style.SUCCESS('Наполнение базы данных завершено!'))

