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


def get_api_answer(timestamp):
    """Запрос к эндпоинту API-сервиса."""
    timestamp = timestamp or int(time.time())
    payload = {'from_date': timestamp}
    logger.info('Произведён запрос к API')
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except requests.RequestException as error:
        logger.error(f'Ошибка при запросе к основному API: {error}')
        raise Exception(f'Ошибка при запросе к основному API: {error}')
    if response.status_code != HTTPStatus.OK:
        status_code = response.status_code
        logger.error(f'Ошибка {status_code}')
        raise exceptions.APIResponseStatusCodeException(f'Ошибка {status_code}')
    try:
        return response.json()
    except ValueError:
        logger.error('Ошибка парсинга ответа из формата json')
        raise ValueError('Ошибка парсинга ответа из формата json')


def check_response(response):
    """Проверка ответа API на соответствие документации."""
    logger.info('Запуск проверки ответа сервера')
    if type(response) is not dict:
        raise TypeError('Ответ API отличен от словаря')
    try:
        homeworks = response['homeworks']
    except KeyError:
        logger.error('Отcутствие ключа homeworks в ответе API-сервиса')
        raise KeyError('Отcутствие ключа homeworks в ответе API-сервиса')
    if type(homeworks) is not list:
        raise TypeError('Несоответствующий тип данных')
    try:
        homework = homeworks[0]
    except IndexError:
        logger.error('Список домашних работ пуст')
        raise IndexError('Список домашних работ пуст')
    return homework


def parse_status(homework):
    """Извлечение статуса домашней работы."""
    homework_status = homework.get('status')
    homework_name = homework.get('homework_name')
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name" в ответе API')
    if 'status' not in homework:
        raise KeyError('Отсутствует ключ "status" в ответе API')
    if homework_status not in HOMEWORK_VERDICTS:
        raise exceptions.HomeworkStatusError(
            f'Неизвестный статус домашней работы: {homework_status}'
        )
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    STATUS = ''
    ERROR_CACHE_MESSAGE = ''
    if not check_tokens():
        logger.critical('Отсутствуют одна или несколько переменных окружения')
        raise Exception('Отсутствуют одна или несколько переменных окружения')
    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = response.get('current_date')
            message = parse_status(check_response(response))
            if message != STATUS:
                send_message(bot, message)
                STATUS = message
            time.sleep(RETRY_PERIOD)
        except Exception as error:
            logger.error(error)
            message_t = str(error)
            if message_t != ERROR_CACHE_MESSAGE:
                send_message(bot, message_t)
                ERROR_CACHE_MESSAGE = message_t
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
