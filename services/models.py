from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.conf import settings


def default_telescopes_list():
    return ["Хаббл", "Кеплер", "Джеймс Уэбб"]


class Comet(models.Model):
    name = models.CharField(max_length=200, verbose_name="Наименование кометы")
    description = models.TextField(verbose_name="Описание расчёта")
    price = models.PositiveIntegerField(verbose_name="Цена расчёта, ₽")
    image_key = models.CharField(max_length=100, verbose_name="Ключ изображения в MinIO", null=True, blank=True)
    is_deleted = models.BooleanField(default=False, verbose_name="Удалена")

    k_x = models.DecimalField(max_digits=8, decimal_places=4, verbose_name="Коэффициент k_x (а.е.)")
    k_y = models.DecimalField(max_digits=8, decimal_places=4, verbose_name="Коэффициент k_y (а.е.)")
    k_z = models.DecimalField(max_digits=8, decimal_places=4, verbose_name="Коэффициент k_z (а.е.)")

    class Meta:
        verbose_name = "Комета"
        verbose_name_plural = "Кометы"

    def __str__(self):
        return self.name

    def get_minio_url(self):
        if self.image_key:
            return f"http://localhost:9002/comets/{self.image_key}"
        return None


class Distance(models.Model):
    
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('deleted', 'Удалён'),
        ('formed', 'Сформирован'),
        ('completed', 'Завершён'),
        ('rejected', 'Отклонён'),
    ]
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="Статус")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    astronomer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_distances', verbose_name="Астроном")
    formed_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата формирования")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата завершения")
    chief_astronomer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='chief_astronomer_distances', verbose_name="Главный астроном")
    telescopes_list = models.JSONField(default=default_telescopes_list, verbose_name="Список телескопов")
    
    def calculated_comets_count(self):
        return self.distance_comets.filter(distance_au__isnull=False).count()

    class Meta:
        verbose_name = "Расчёт расстояния"
        verbose_name_plural = "Расчёты расстояний"
        constraints = [
            models.UniqueConstraint(
                fields=['astronomer'],
                condition=models.Q(status='draft'),
                name='unique_draft_per_astronomer'
            )
        ]

    def __str__(self):
        return f"Расчёт расстояния #{self.id}"

    def total_items(self):
        return self.distance_comets.count()

    def clean(self):
        if self.status == 'draft':
            existing_draft = Distance.objects.filter(
                astronomer=self.astronomer, 
                status='draft'
            ).exclude(pk=self.pk)
            if existing_draft.exists():
                raise ValidationError("У астронома уже есть заявка в статусе черновик")


class RequestComet(models.Model):

    request = models.ForeignKey(Distance, on_delete=models.CASCADE, related_name='distance_comets')
    comet = models.ForeignKey(Comet, on_delete=models.CASCADE)
    sort_order = models.PositiveIntegerField(default=1, verbose_name="Порядок")
    coords_x = models.DecimalField(max_digits=6, decimal_places=3, verbose_name="Координата X")
    coords_y = models.DecimalField(max_digits=6, decimal_places=3, verbose_name="Координата Y")
    coords_z = models.DecimalField(max_digits=6, decimal_places=3, verbose_name="Координата Z")
    distance_au = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Расстояние от Солнца, а.е.")

    class Meta:
        verbose_name = "Комета в заявке"
        verbose_name_plural = "Кометы в заявках"
        unique_together = ['request', 'comet']

    def __str__(self):
        return f"{self.comet.name} в заявке #{self.request.id}"

