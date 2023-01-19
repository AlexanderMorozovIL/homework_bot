import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

import exceptions

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler = logging.FileHandler(f'{__name__}.log', encoding='UTF-8')
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)

handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    """Проверка доступности переменных окружения."""
    ENV_VARS = {
        'practicum_token': PRACTICUM_TOKEN,
        'telegram_token': TELEGRAM_TOKEN,
        'telegram_chat_id': TELEGRAM_CHAT_ID
    }
    for key, value in ENV_VARS.items():
        if value is None:
            logger.critical(f'{key} не найден!')
            return False
    return True


def send_message(bot, message):
    """Отправка сообщение в Telegram чат."""
    logger.info('Отправка сообщения в Telegram')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Удачная отправка сообщения! {message}')
    except Exception as error:
        logger.error(f'Ошибка при отправке сообщения: {error}')
        raise exceptions.SendMessageError(
            f'Ошибка при отправке сообщения: {error}'
        )


def get_api_answer(timestamp):
    """Запрос к эндпоинту API-сервиса."""
    timestamp = timestamp or int(time.time())
    payload = {'from_date': timestamp}
    logger.info('Начинаем делать запрос к API')
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except requests.RequestException as error:
        raise exceptions.RequestAPIError(
            f'Ошибка при запросе к основному API: {error}'
        )
    if response.status_code != HTTPStatus.OK:
        status_code = response.status_code
        raise exceptions.APIResponseStatusCodeException(
            f'Ошибка {status_code}'
        )
    try:
        response = response.json()
        return response
    except ValueError:
        raise ValueError('Ошибка парсинга ответа из формата json')


def check_response(response):
    """Проверка ответа API на соответствие документации."""
    logger.info('Запуск проверки ответа сервера')
    if not isinstance(response, dict):
        raise TypeError('Ответ API отличен от словаря')
    if 'current_date' not in response:
        raise KeyError('Отсутствует ключ current_date в ответе API-сервиса')
    if 'homeworks' not in response:
        raise KeyError('Отсутствует ключ homeworks в ответе API-сервиса')
    timestamp = response['current_date']
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError('Несоответствующий тип данных')
    if not isinstance(timestamp, int):
        raise TypeError('Несоответствующий тип данных')
    return homeworks


def parse_status(homework):
    """Извлечение статуса домашней работы."""
    homework_status = homework.get('status')
    homework_name = homework.get('homework_name')
    if homework_status is None:
        raise exceptions.HomeworkStatusNoneError(
            'Статус домашней работы не обнаружен'
        )
    if homework_name is None:
        raise exceptions.HomeworkNameError(
            'Неизвестно имя домашней работы'
        )
    if homework_status not in HOMEWORK_VERDICTS:
        raise exceptions.UnknownHomeworkStatusError(
            'Неизвестный статус домашней работы'
        )
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    return ('Изменился статус проверки '
            f'работы "{homework_name}". {verdict}')


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствуют одна или несколько переменных окружения')
        exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    last_status = None

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                if message != last_status:
                    send_message(bot, message)
                    last_status = message
                else:
                    logger.info('Статус домашней работы не изменился...')
            else:
                logger.info('Домашних работ не найдено!')
            current_timestamp = response.get('current_date')
        except exceptions.SendMessageError as error:
            logger.error(f'Ошибка при отправке сообщения: {error}')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if last_status != message:
                send_message(bot, message)
                last_status = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
