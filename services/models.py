from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


def default_astronomers_list():
    """Дефолтный список астрономов для каждой новой заявки."""
    return ["Судьи В. Г.", "Коваленко А. И.", "Петров С. М."]


def default_telescopes_list():
    """Дефолтный список телескопов для каждой новой заявки."""
    return ["Хаббл", "Кеплер", "Джеймс Уэбб"]


class Comet(models.Model):
    """Комета для расчёта гелиоцентрического расстояния"""
    name = models.CharField(max_length=200, verbose_name="Наименование кометы")
    description = models.TextField(verbose_name="Описание расчёта")
    price = models.PositiveIntegerField(verbose_name="Цена расчёта, ₽")
    image_key = models.CharField(max_length=100, verbose_name="Ключ изображения в MinIO", null=True, blank=True)
    is_deleted = models.BooleanField(default=False, verbose_name="Удалена")
    # Поправочные коэффициенты для расчёта расстояния до Солнца
    k_x = models.DecimalField(max_digits=8, decimal_places=4, verbose_name="Коэффициент k_x (а.е.)")
    k_y = models.DecimalField(max_digits=8, decimal_places=4, verbose_name="Коэффициент k_y (а.е.)")
    k_z = models.DecimalField(max_digits=8, decimal_places=4, verbose_name="Коэффициент k_z (а.е.)")

    class Meta:
        verbose_name = "Комета"
        verbose_name_plural = "Кометы"

    def __str__(self):
        return self.name

    def get_minio_url(self):
        """Построение URL изображения в MinIO"""
        if self.image_key:
            return f"http://localhost:9002/comets/{self.image_key}"
        return None


class CalculationRequest(models.Model):
    """Заявка на расчёты гелиоцентрического расстояния комет"""
    
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('deleted', 'Удалён'),
        ('formed', 'Сформирован'),
        ('completed', 'Завершён'),
        ('rejected', 'Отклонён'),
    ]
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="Статус")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    astronomer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_requests', verbose_name="Астроном")
    formed_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата формирования")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата завершения")
    moderator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='moderated_requests', verbose_name="Модератор")
    astronomers_list = models.JSONField(default=default_astronomers_list, verbose_name="Список астрономов")
    telescopes_list = models.JSONField(default=default_telescopes_list, verbose_name="Список телескопов")
    total_distance_au = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Общее расстояние, а.е.")

    class Meta:
        verbose_name = "Заявка на расчёт"
        verbose_name_plural = "Заявки на расчёты"
        constraints = [
            models.UniqueConstraint(
                fields=['astronomer'],
                condition=models.Q(status='draft'),
                name='unique_draft_per_astronomer'
            )
        ]

    def __str__(self):
        return f"Заявка #{self.id}"

    def total_items(self):
        """Количество комет в заявке"""
        return sum(item.quantity for item in self.request_comets.all())

    def clean(self):
        """Валидация: не более одной заявки в статусе черновик на астронома"""
        if self.status == 'draft':
            existing_draft = CalculationRequest.objects.filter(
                astronomer=self.astronomer, 
                status='draft'
            ).exclude(pk=self.pk)
            if existing_draft.exists():
                raise ValidationError("У астронома уже есть заявка в статусе черновик")


class RequestComet(models.Model):
    """Связь заявки и кометы с дополнительными полями"""
    request = models.ForeignKey(CalculationRequest, on_delete=models.CASCADE, related_name='request_comets')
    comet = models.ForeignKey(Comet, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, verbose_name="Количество")
    sort_order = models.PositiveIntegerField(default=1, verbose_name="Порядок")
    is_main = models.BooleanField(default=False, verbose_name="Главная")
    coords_x = models.DecimalField(max_digits=6, decimal_places=3, verbose_name="Координата X")
    coords_y = models.DecimalField(max_digits=6, decimal_places=3, verbose_name="Координата Y")
    coords_z = models.DecimalField(max_digits=6, decimal_places=3, verbose_name="Координата Z")

    class Meta:
        verbose_name = "Комета в заявке"
        verbose_name_plural = "Кометы в заявках"
        unique_together = ['request', 'comet']

    def __str__(self):
        return f"{self.comet.name} в заявке #{self.request.id}"

