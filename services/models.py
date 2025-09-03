from django.db import models


class Service(models.Model):
    """Услуга расчёта расстояния кометы - атомарная модель (1НФ)"""
    name = models.CharField(max_length=200, verbose_name="Наименование")
    price = models.PositiveIntegerField(verbose_name="Цена, ₽")
    event_date = models.DateField(verbose_name="Дата события")
    description = models.TextField(verbose_name="Описание")
    image_key = models.CharField(max_length=100, verbose_name="Ключ изображения в MinIO")

    class Meta:
        verbose_name = "Услуга"
        verbose_name_plural = "Услуги"

    def __str__(self):
        return self.name

    def get_minio_url(self):
        """Построение URL изображения в MinIO"""
        return f"http://localhost:9000/comets/{self.image_key}"


class Order(models.Model):
    """Заявка на расчёты"""
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создана")

    class Meta:
        verbose_name = "Заявка"
        verbose_name_plural = "Заявки"

    def __str__(self):
        return f"Заявка #{self.id}"

    def total_items(self):
        """Количество услуг в заявке"""
        return sum(item.quantity for item in self.items.all())


class OrderItem(models.Model):
    """Элемент заявки - связь многие-ко-многим с дополнительными полями"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, verbose_name="Количество")
    sort_order = models.PositiveIntegerField(default=1, verbose_name="Порядок")
    is_main = models.BooleanField(default=False, verbose_name="Главный")

    class Meta:
        verbose_name = "Элемент заявки"
        verbose_name_plural = "Элементы заявки"
        unique_together = ['order', 'service']

    def __str__(self):
        return f"{self.service.name} в заявке #{self.order.id}"
