class SendMessageError(Exception):
    """Ошибка при отправке сообщения."""

    pass


class RequestAPIError(Exception):
    """Ошибка при запросе к API-сервисаю."""

    pass


class APIResponseStatusCodeException(Exception):
    """Несоответствующий статус ответа эндпоинта."""

    pass


class HomeworkStatusNoneError(Exception):
    """Статус домашней работы не обнаружен."""

    pass


class UnknownHomeworkStatusError(Exception):
    """Неизвестный статус домашней работы."""

    pass


class HomeworkNameError(Exception):
    """Название домашней работы не соответствует ожидаемому."""

    pass
