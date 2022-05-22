
import os
import sys
import telegram
import time
import logging
import requests
from dotenv import load_dotenv


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())


def send_message(bot, message):
    """Отправляет сообщение в чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info(f'Сообщение "{message}" удачно отправлено')
    except Exception:
        logger.error(f'Сообщение "{message}" не отправлено')


class NotApiException(Exception):
    """Собственная ошибка."""

    pass


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту и возвращает ответ в формат JSON."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != 200:
        logger.error('Эндпоинт недоступен')
        raise NotApiException('Эндпоинт недоступен')
    else:
        return response.json()


def check_response(response) -> dict:
    """ПРоверяет ответ API на корректность и возвращает список ДЗ."""
    if not isinstance(response, dict):
        raise TypeError('Не словарь')
    if 'homeworks' not in response:
        logging.error('Нет ключа homeworks')
        raise KeyError('Нет ключа homeworks')
    homework = response['homeworks']
    if not isinstance(homework, list):
        raise TypeError('по ключу лежит не список')
    return homework


def parse_status(homework):
    """Проверяет статус домашки."""
    if 'homework_name' not in homework:
        raise KeyError('Нет ключа homework_name')
    homework_name = homework['homework_name']
    if 'status' not in homework:
        raise KeyError('Нет ключа status')
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES[homework_status]
    if homework_status not in HOMEWORK_STATUSES:
        logger.error('Неизвестный статус')
        raise KeyError(f'Неизвестный статус: {homework_status}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет наичие токенов."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствуют переменные окружения!')
        raise SystemExit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    message_status = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            logger.info('Домашняя работа.')
            if homework:
                message = parse_status(homework[0])
                if message != message_status:
                    send_message(bot, message)
                    message_status = message
                current_timestamp = int(time.time())
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message != message_status:
                send_message(bot, message)
                message_status = message
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        stream=sys.stdout,
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    main()
