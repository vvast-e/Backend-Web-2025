

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Comet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Наименование кометы')),
                ('description', models.TextField(verbose_name='Описание расчёта')),
                ('price', models.PositiveIntegerField(verbose_name='Цена расчёта, ₽')),
                ('image_key', models.CharField(blank=True, max_length=100, null=True, verbose_name='Ключ изображения в MinIO')),
                ('is_deleted', models.BooleanField(default=False, verbose_name='Удалена')),
                ('non_grav_params', models.JSONField(default=list, verbose_name='Негравитационные параметры')),
            ],
            options={
                'verbose_name': 'Комета',
                'verbose_name_plural': 'Кометы',
            },
        ),
        migrations.CreateModel(
            name='CalculationRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('draft', 'Черновик'), ('deleted', 'Удалён'), ('formed', 'Сформирован'), ('completed', 'Завершён'), ('rejected', 'Отклонён')], default='draft', max_length=20, verbose_name='Статус')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('formed_at', models.DateTimeField(blank=True, null=True, verbose_name='Дата формирования')),
                ('completed_at', models.DateTimeField(blank=True, null=True, verbose_name='Дата завершения')),
                ('astronomer_name', models.CharField(default='Судьи В. Г.', max_length=100, verbose_name='Имя астронома')),
                ('telescope_name', models.CharField(default='Хаббл', max_length=100, verbose_name='Название телескопа')),
                ('total_distance_au', models.DecimalField(blank=True, decimal_places=3, max_digits=10, null=True, verbose_name='Общее расстояние, а.е.')),
                ('astronomer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_requests', to=settings.AUTH_USER_MODEL, verbose_name='Астроном')),
                ('moderator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='moderated_requests', to=settings.AUTH_USER_MODEL, verbose_name='Модератор')),
            ],
            options={
                'verbose_name': 'Заявка на расчёт',
                'verbose_name_plural': 'Заявки на расчёты',
            },
        ),
        migrations.CreateModel(
            name='RequestComet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(default=1, verbose_name='Количество')),
                ('sort_order', models.PositiveIntegerField(default=1, verbose_name='Порядок')),
                ('is_main', models.BooleanField(default=False, verbose_name='Главная')),
                ('coords_x', models.DecimalField(decimal_places=3, max_digits=6, verbose_name='Координата X')),
                ('coords_y', models.DecimalField(decimal_places=3, max_digits=6, verbose_name='Координата Y')),
                ('coords_z', models.DecimalField(decimal_places=3, max_digits=6, verbose_name='Координата Z')),
                ('comet', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='services.comet')),
                ('request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='request_comets', to='services.calculationrequest')),
            ],
            options={
                'verbose_name': 'Комета в заявке',
                'verbose_name_plural': 'Кометы в заявках',
            },
        ),
        migrations.AddConstraint(
            model_name='calculationrequest',
            constraint=models.UniqueConstraint(condition=models.Q(('status', 'draft')), fields=('astronomer',), name='unique_draft_per_astronomer'),
        ),
        migrations.AlterUniqueTogether(
            name='requestcomet',
            unique_together={('request', 'comet')},
        ),
    ]