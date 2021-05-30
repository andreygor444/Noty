from threading import Thread
from time import sleep
from Noty import (load_notifys,
                  NotificationError)
import datetime as dt
import os


def check_file():
    """Эта функция служит для того чтобы завершать работу
       этого фонового модуля, когда запускается основной модуль Noty"""
    while True:
        try:
            with open('state.txt', 'r', encoding='utf-8') as f:
                state = f.read()
                if state == 'working':
                    os._exit(0)
        except FileNotFoundError:
            with open('state.txt', 'r', encoding='utf-8') as f:
                f.write('closed')
        sleep(1)


def background_work(notifys):
    """Эта функция отвечает за отправку уведомлений
       когда основной модуль закрыт"""
    notifys_times = {}
    # В этом словаре будут храниться пары "время напоминания: напоминание"
    for notify in notifys:
        try:
            notifys_times[notify.next_time()] = notify
        except NotificationError:
            continue
    while True:
        # Основной цикл фонового модуля.
        # Постоянно проверяет текущее время,
        # и когда видит что на это время(+-5 секунд) назначено напоминание -
        # присылает его
        current_time = dt.datetime.now()
        arrive_notifys = [time for time in notifys_times.keys() if (time - current_time).total_seconds() <= 5]
        for time in arrive_notifys:
            notify = notifys_times[time]
            notify.notify()
            try:
                notifys_times[notify.next_time()] = notify
            except NotificationError:
                pass
            del notifys_times[time]
        sleep(5)


if __name__ == '__main__':
    # Подгрузка напоминаний
    notifications = load_notifys()
    # Запуск потока, присылающего напоминания
    Thread(target=background_work, args=[notifications]).start()
    check_file()
