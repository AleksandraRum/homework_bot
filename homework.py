
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
    homework = response.get('homeworks')
    if isinstance(homework, list):
        return homework
    else:
        raise TypeError('по ключу лежит не список')


def parse_status(homework):
    """Проверяет статус домашки."""
    if 'homework_name' in homework:
        homework_name = homework['homework_name']
    else:
        raise KeyError('Нет ключа homework_name')
    if 'status' in homework:
        homework_status = homework['status']
    else:
        raise KeyError('Нет ключа status')
    try:
        verdict = HOMEWORK_STATUSES[homework_status]
    except homework_status not in HOMEWORK_STATUSES:
        logger.error('Неизвестный статус')
        raise KeyError(f'Неизвестный статус: {homework_status}')
    except homework_status not in homework:
        logger.error('Отсутствует статус')
        raise KeyError(f'Отсутствует статус: {homework_status}')
    else:
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
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            logger.info('Домашняя работа.')
            if homework:
                message = parse_status(homework)
                send_message(bot, message)
                current_timestamp = int(time.time())
                # # time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    logging.basicConfig(
        stream=sys.stdout,
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger.addHandler(logging.StreamHandler())
    main()
