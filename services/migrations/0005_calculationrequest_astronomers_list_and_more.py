

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0004_remove_calculationrequest_astronomer_ref_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='calculationrequest',
            name='astronomers_list',
            field=models.JSONField(default=list, verbose_name='Список астрономов'),
        ),
        migrations.AddField(
            model_name='calculationrequest',
            name='telescopes_list',
            field=models.JSONField(default=list, verbose_name='Список телескопов'),
        ),
    ]