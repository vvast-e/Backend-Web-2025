from typing import Optional, Tuple

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
import redis


class RedisSessionAuthentication(BaseAuthentication):
    """Аутентификация по cookie 'session_id' через Redis.
    В Redis по ключу session_id хранится email пользователя.
    """

    def __init__(self) -> None:
        self._redis = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
        self._user_model = get_user_model()

    def authenticate(self, request) -> Optional[Tuple[object, None]]:
        session_id = request.COOKIES.get('session_id')
        if not session_id:
            return None
        try:
            # Проверка на отзыв сессии (blacklist)
            if self._redis.exists(f"bl:{session_id}"):
                return None
            email_bytes = self._redis.get(session_id)
        except Exception:
            # Если Redis недоступен, не блокируем гостевой доступ
            return None
        if not email_bytes:
            return None
        email = email_bytes.decode('utf-8') if isinstance(email_bytes, (bytes, bytearray)) else str(email_bytes)
        try:
            user = self._user_model.objects.get(email=email)
        except self._user_model.DoesNotExist:
            return None
        return (user, None)


