class APIResponseStatusCodeException(Exception):
    """Несоответствующий статус ответа эндпоинта."""

    pass


class HomeworkStatusError(Exception):
    """Неизвестный статус домашней работы."""

    pass
