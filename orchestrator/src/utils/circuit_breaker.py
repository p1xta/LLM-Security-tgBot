import time
from functools import wraps
from typing import Callable, Any, Optional
import logging
from ..exceptions.specific import ServiceUnavailableError

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """Реализация паттерна Circuit Breaker для устойчивости к сбоям сервисов"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.last_failure_time: Optional[float] = None
    
    def can_execute(self) -> bool:
        """Проверяет, можно ли выполнить запрос в текущем состоянии Circuit Breaker"""
        if self.state == "CLOSED":
            return True
        
        if self.state == "OPEN":
            # Проверяем, не истек ли таймаут восстановления
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker transitioning to HALF_OPEN state")
                return True
            return False
        
        # HALF_OPEN - разрешаем одну попытку
        return True
    
    def record_success(self):
        """Регистрирует успешный вызов"""
        if self.state == "HALF_OPEN":
            # Успех в HALF_OPEN состоянии возвращает в CLOSED
            self.state = "CLOSED"
            self.failures = 0
            self.last_failure_time = None
            logger.info("Circuit breaker reset to CLOSED state after successful call")
        elif self.state == "CLOSED":
            # Сбрасываем счетчик ошибок при успешных вызовах
            self.failures = 0
    
    def record_failure(self):
        """Регистрирует неудачный вызов"""
        self.failures += 1
        self.last_failure_time = time.time()
        
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit breaker opened after {self.failures} failures")
        
        if self.state == "HALF_OPEN":
            # Неудача в HALF_OPEN состоянии возвращает в OPEN
            self.state = "OPEN"
            logger.warning("Circuit breaker returned to OPEN state after failed half-open attempt")

def with_circuit_breaker(failure_threshold: int = 5, recovery_timeout: int = 30):
    """
    Декоратор для применения Circuit Breaker к функциям
    
    Args:
        failure_threshold: Количество ошибок до перехода в OPEN состояние
        recovery_timeout: Время в секундах до попытки восстановления
        
    Returns:
        Декорированную функцию с Circuit Breaker
    """
    circuit_breaker = CircuitBreaker(failure_threshold, recovery_timeout)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            if not circuit_breaker.can_execute():
                logger.warning("Circuit breaker is OPEN, request blocked")
                raise ServiceUnavailableError("Service temporarily unavailable due to previous failures")
            
            try:
                result = await func(*args, **kwargs)
                circuit_breaker.record_success()
                return result
            except Exception as e:
                circuit_breaker.record_failure()
                raise e
        
        return async_wrapper
    
    return decorator