class SendMessageError(Exception):
    """Ошибка при отправке сообщения."""

    pass


class RequestAPIError(Exception):
    """Ошибка при запросе к API-сервисаю."""

    pass


class APIResponseStatusCodeException(Exception):
    """Несоответствующий статус ответа эндпоинта."""

    pass


class HomeworkStatusError(Exception):
    """Неизвестный статус домашней работы."""

    pass


class HomeworkNameError(Exception):
    """Название домашней работы не соответствует ожидаемому."""

    pass
