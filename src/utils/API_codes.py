from src.utils.utils import error, log, logger
import asyncio

def get_api_error_message(status_code: int) -> str:
    if status_code == 404:
        logger.warning("Ресурс не найден (404).")
        return "Ресурс не найден (404)."
    elif status_code == 403:
        logger.warning("Доступ запрещен (403).")
        return "Доступ запрещен (403). Пожалуйста, попробуйте позже."
    elif status_code == 400:
        logger.warning("Некорректный запрос (400).")
        return "Некорректный запрос (400). Пожалуйста, проверьте параметры запроса."
    elif status_code == 401:
        logger.warning("Неавторизованный доступ (401).")
        return "Неавторизованный доступ (401). Пожалуйста, проверьте токен или ключ API."
    elif status_code == 429:
        logger.warning("Слишком много запросов (429).")
        return "Слишком много запросов (429). Пожалуйста, попробуйте позже."
    elif status_code == 408:
        logger.warning("Время ожидания запроса истекло (408).")
        return "Время ожидания запроса истекло (408). Пожалуйста, попробуйте позже."
    elif status_code == 502:
        logger.warning("Плохой шлюз (502).")
        return "Плохой шлюз (502). Пожалуйста, попробуйте позже."
    elif status_code == 504:
        logger.warning("Шлюз не отвечает (504).")
        return "Шлюз не отвечает (504). Пожалуйста, попробуйте позже."
    elif status_code == 422:
        logger.warning("Невозможно обработать запрос (422).")
        return "Невозможно обработать запрос (422). Пожалуйста, проверьте параметры запроса."
    elif status_code == 415:
        logger.warning("Неподдерживаемый тип медиа (415).")
        return "Неподдерживаемый тип медиа (415). Пожалуйста, проверьте заголовки запроса."
    elif status_code == 429:
        logger.warning("Слишком много запросов (429).")
        return "Слишком много запросов (429). Пожалуйста, попробуйте позже."
    elif status_code == 500:
        logger.warning("Внутренняя ошибка сервера (500).")
        return "Внутренняя ошибка сервера (500). Пожалуйста, попробуйте позже."
    elif status_code == 503:
        logger.warning("Сервис временно недоступен (503).")
        return "Сервис временно недоступен (503). Пожалуйста, попробуйте позже."
    else:
        logger.warning(f"Произошла ошибка с кодом {status_code}.")
        return f"Произошла ошибка с кодом {status_code}. Пожалуйста, попробуйте позже."

