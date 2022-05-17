
import os
import sys
import telegram
import time
import logging
import requests
from requests import RequestException
from dotenv import load_dotenv


load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(
    stream=sys.stdout,
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO)
logger.addHandler(logging.StreamHandler())


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = 636828395

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в чат"""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info(f'Сообщение "{message}" удачно отправлено')
    except Exception:
        logger.error(f'Сообщение "{message}" не отправлено')


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту и возвращает ответ в формат JSON"""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != 200:
            logger.error('Эндпоинт недоступен')
            raise Exception('Эндпоинт недоступен')
    except RequestException as error:
        logging.error(error)
        raise RequestException('Ошибка ответа от сервера')
    else:
        return response.json()


def check_response(response) -> dict:
    """ПРоверяет ответ API на корректность и возвращает список ДЗ"""
    try:
        homeworks = response['homeworks']
    except IndexError:
        logging.error('Нет ключа homeworks')
        raise IndexError('Нет ключа homeworks')
    else:
        if type(homeworks) != list:
            raise TypeError('ДЗ не список')
        else:
            return homeworks


def parse_status(homework) -> str:
    homework_name = homework['homework_name']
    homework_status = homework['status']
    STATUS_HOMEWORK = None

    if not homework_name:
        raise ValueError('Нет обнаружено homework_name')
    if not homework_status:
        raise ValueError('Нет обнаружен status')
    if STATUS_HOMEWORK != homework_status:
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        return logger.debug('Статус ДЗ не обновлен')


def check_tokens() -> bool:
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True
    else:
        logging.critical('Отсутствуют переменные окружения!')
        return False


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            check_tokens()
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            logger.info('Домашняя работа.')
            message = parse_status(homework[0])
            send_message(bot, message)
            current_timestamp: int = int(time.time())
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
