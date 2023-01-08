import logging
import os
import time

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

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)


def check_tokens():
    """Проверка доступности переменных окружения."""
    ENV_VARS = {'practicum_token': PRACTICUM_TOKEN,
                'telegram_token': TELEGRAM_TOKEN,
                'telegram_chat_id': TELEGRAM_CHAT_ID}
    for key, value in ENV_VARS.items():
        if value is None:
            logging.critical(f'{key} не найден!')
            return False
    return True


def send_message(bot, message):
    """Отправка сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Удачная отправка сообщения! {message}')
    except Exception as error:
        logging.error(f'Ошибка при отправке сообщения: {error}')


def get_api_answer(timestamp):
    """Запрос к эндпоинту API-сервиса."""
    timestamp = timestamp or int(time.time())
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except requests.RequestException:
        logging.error('Сбой при запросе к эндпоинту')
    if response.status_code != 200:
        raise exceptions.APIResponseStatusCodeException(
            'Сбой при запросе к эндпоинту')
    return response.json()


def check_response(response):
    """Проверка ответа API на соответствие документации."""
    try:
        timestamp = response['current_date']
    except KeyError:
        logging.error('Отыутствие ключа current_date в ответе API-сервиса')
    try:
        homeworks = response['homeworks']
    except KeyError:
        logging.error('Отыутствие ключа homeworks в ответе API-сервиса')
    if isinstance(timestamp, int) and isinstance(homeworks, list):
        return homeworks
    else:
        raise TypeError('Несоответствующий тип данных')


def parse_status(homework):
    """Извлечение статуса домашней работы."""
    homework_status = homework.get('status')
    homework_name = homework.get('homework_name')

    if homework_status is not None and homework_name is not None:
        if homework_status in HOMEWORK_VERDICTS:
            verdict = HOMEWORK_VERDICTS.get(homework_status)
            return ('Изменился статус проверки '
                    + f'работы "{homework_name}". {verdict}')
        else:
            raise SystemError('Неизвестный статус домашней работы')
    else:
        raise KeyError('Hет нужных ключей в словаре')


def main():
    """Основная логика работы бота."""
    if check_tokens():
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        timestamp = int(time.time())

        while True:
            try:
                response = get_api_answer(timestamp)
                homeworks = check_response(response)
                number_of_homeworks = len(homeworks)
                while number_of_homeworks > 0:
                    message = parse_status(homeworks[number_of_homeworks - 1])
                    send_message(bot, message)
                    number_of_homeworks -= 1
                timestamp = int(time.time())
                time.sleep(RETRY_PERIOD)

            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                send_message(bot, message)
                time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
