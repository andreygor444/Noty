from PyQt5.QtWidgets import (QApplication, QWidget, QScrollArea,
                             QVBoxLayout, QGroupBox, QLabel, QCheckBox,
                             QPushButton, QSizePolicy, QHBoxLayout)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QCursor, QIcon
from PyQt5 import uic
from functools import partial
import os
import sys
import json
import datetime as dt
import subprocess
import sqlite3
import ui_resources


class NotificationError(Exception):
    """Вызывается только из класса напоминания, если возникли какие-то проблемы"""
    pass


class Notification:
    def __init__(self, time, title, text,
                 included=True, week_days=None, month_dates=None,
                 repeating_mode=0, song='default'):
        if month_dates is None:
            month_dates = []
        if week_days is None:
            week_days = [True for _ in range(1, 8)]
        self.time = time  # День, час и минута напоминания
        self.title = title  # Заголовок
        self.text = text  # Некоторое пояснение к оповещению
        self.included = included  # Состояние оповезения: вкл/выкл(bool)
        self.week_days = week_days  # Дни недели, в которые приходит напоминание
        self.month_dates = month_dates  # Конеретные даты, в которые приходит напоминание
        self.repeating_mode = repeating_mode
        # Режим повтора. 0 - напоминание приходит 1 раз, после чего выключается
        #                1 - напоминание приходит в определённые дни недели
        #                2 - напоминание приходит в определённые даты,
        #                установленные пользователем
        self.song = song  # Мелодия напоминания

    def notify(self):
        """Присылает напоминание"""
        # Запускается скомпилированный .exe файл notify, отображающий уведомление
        # Заголовок, текст и мелодия оповещения передаются как агрументы командной строки
        command = f'notify title="{self.title}" text="{self.text}" song="{self.song}"'
        subprocess.Popen(command)

    def next_time(self):
        """Возвращает ближайшее время прихода напоминания,
           либо вызывает NotificationError"""
        assert self.repeating_mode in (0, 1, 2), 'Нарушение инварианта для режима повторения'
        if self.included:
            current_time = dt.datetime.now()
            if self.repeating_mode == 0:
                time = self.time
            elif self.repeating_mode == 1:
                current_week_day = dt.date.today().weekday()
                for delta_days, state in enumerate(
                        self.week_days[current_week_day:] + self.week_days[:current_week_day]
                ):
                    if state:
                        current_day = current_time.day
                        current_month = current_time.month
                        current_year = current_time.year
                        time = dt.datetime(current_year,
                                           current_month,
                                           current_day,
                                           self.time.hour,
                                           self.time.minute
                                           ) + dt.timedelta(delta_days)
                        if time > current_time:
                            break
                else:
                    time = current_time - dt.timedelta(1)
            else:
                time = min(self.month_dates)
                time = dt.datetime(time.year, time.month, time.day,
                                   self.time.hour, self.time.minute)
            if time > current_time:
                return time
            else:
                raise NotificationError('Время отправки оповещения уже прошло')
        else:
            raise NotificationError('Оповещение отключено')


class NotifyWidget(QWidget):
    """Кастомный виджет напоминаний
       (из этих виджетов состоит список напоминаний на главном окне)"""

    def __init__(self, notify, main_class):
        super().__init__()
        self.notify = notify
        self.main_class = main_class
        self.initUi()

    def initUi(self):
        self.setStyleSheet('''border-top: 4px solid black;
                              border-bottom: 4px solid black;
                              ''')
        on_button_cursor = QCursor(Qt.PointingHandCursor)
        self.widget_list = QHBoxLayout(self)
        self.widget_list.setSpacing(0)
        time = self.notify.time
        self.time_label = QLabel(time.strftime('%H:%M'), self)
        self.time_label.setFont(QFont('Arial', 20))
        self.time_label.setMinimumSize(100, 50)
        self.time_label.setMaximumHeight(50)
        self.time_label.setStyleSheet('''background: none;
                                         background-color: rgb(240, 240, 240);
                                         border-left: 4px solid black;
                                         border-top-left-radius: 30px;
                                         ''')
        self.widget_list.addWidget(self.time_label)
        self.title_label = QLabel(self.notify.title)
        title_length = len(self.notify.title)
        self.title_label.setFont(QFont('Arial', 14))
        self.title_label.setMinimumSize(140, 50)
        self.title_label.setMaximumHeight(50)
        self.title_label.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Preferred)
        self.title_label.setStyleSheet('''background: none;
                                          background-color: rgb(240, 240, 240);
                                          ''')
        self.widget_list.addWidget(self.title_label)
        self.settings_btn = QPushButton('⚙  ', self)
        self.settings_btn.setMaximumWidth(40)
        self.settings_btn.setMinimumHeight(50)
        self.settings_btn.setCursor(on_button_cursor)
        self.settings_btn.clicked.connect(self.edit_notify)
        self.settings_btn.setStyleSheet('''background: none;
                                           background-color: rgb(240, 240, 240);
                                           ''')
        self.widget_list.addWidget(self.settings_btn)
        self.switch = QCheckBox(self)
        self.switch.setMaximumWidth(25)
        self.switch.setMinimumHeight(50)
        self.switch.setChecked(self.notify.included)
        self.switch.setCursor(on_button_cursor)
        self.switch.stateChanged.connect(self.change_state)
        self.switch.setStyleSheet('''background: none;
                                     background-color: rgb(240, 240, 240);
                                     ''')
        self.widget_list.addWidget(self.switch)
        self.delete_btn = QPushButton('✖ ', self)
        self.delete_btn.setFont(QFont('Arial', 14))
        self.delete_btn.setMaximumWidth(40)
        self.delete_btn.setMinimumHeight(50)
        self.delete_btn.setCursor(on_button_cursor)
        self.delete_btn.clicked.connect(partial(self.main_class.remove_notify, self))
        self.delete_btn.setStyleSheet('''background: none;
                                         background-color: rgb(240, 240, 240);
                                         border-right: 4px solid black;
                                         color: rgb(200, 50, 20);
                                         border-bottom-right-radius: 30px;
                                         ''')
        self.widget_list.addWidget(self.delete_btn)

    def change_state(self):
        """Включает/выключает напоминание и запускает/сбрасывает таймер"""
        self.notify.included = not self.notify.included
        self.main_class.set_timer(self.notify)

    def edit_notify(self, new_notify=False):
        self.edit_notify_window = EditNotifyWindow(self.notify, new_notify)
        self.edit_notify_window.show()


class EditNotifyWindow(QWidget):
    """Класс окна создания/редактирования напоминания"""

    def __init__(self, notify, is_new=False):
        super().__init__()
        self.notify = notify
        self.is_new = is_new  # True в том случае, когда создаётся новое напоминание
        self.week_days = self.notify.week_days.copy()
        self.month_dates = self.notify.month_dates.copy()
        uic.loadUi('resources\\ui\\EditNotifyWindow.ui', self)
        self.save = False  # Переменная save нужна чтобы closeEvent понимал
        # когда нажата кнопка "Закрыть", а когда "Сохранить"
        self.initUi()

    def initUi(self):
        icon = QIcon(os.getcwd() + '\\resources\\images\\settings_window_icon.ico')
        self.setWindowIcon(icon)
        self.week_buttons = (self.pn_btn, self.vt_btn, self.sr_btn,
                             self.cht_btn, self.pt_btn, self.sb_btn,
                             self.vs_btn)
        self.setLayout(self.main_layout)
        self.title_line.setText(self.notify.title)
        self.plain_text.insertPlainText(self.notify.text)
        time = self.notify.time
        self.hours_label.setText(time.strftime('%H'))
        self.minutes_label.setText(time.strftime('%M'))
        self.repeat_switch.stateChanged.connect(self.change_repeating)
        self.week_selection_switch.clicked.connect(self.change_repeating)
        self.calendar_selection_switch.clicked.connect(self.change_repeating)
        self.ringtone_switch.stateChanged.connect(
            lambda state: self.ringtone_selector.setEnabled(state))
        if self.notify.repeating_mode == 1:
            self.repeat_switch.setChecked(True)
        elif self.notify.repeating_mode == 2:
            self.repeat_switch.setChecked(True)
            self.calendar_selection_switch.setChecked(True)
            self.calendar_selection_btn.setEnabled(True)
            for button in self.week_buttons:
                button.setEnabled(False)
        if self.notify.song is None:
            self.ringtone_switch.setCheckState(False)
        self.enlarge_hours_btn.clicked.connect(self.enlarge_hours)
        self.enlarge_minutes_btn.pressed.connect(self.enlarge_minutes)
        self.reduce_hours_btn.clicked.connect(self.reduce_hours)
        self.reduce_minutes_btn.clicked.connect(self.reduce_minutes)
        for index, button in enumerate(self.week_buttons):
            button.clicked.connect(self.select_week_date)
            if not self.week_days[index]:
                button.setStyleSheet('''border: 3px solid;
                                        border-radius: 15px;
                                        background-color: rgb(108, 108, 108);
                                        ''')
        self.calendar_selection_btn.clicked.connect(self.select_calendar_dates)
        if self.notify.song:
            self.ringtone_selector.setCurrentText(self.notify.song)
        self.apply_btn.clicked.connect(self.apply)
        self.close_btn.clicked.connect(self.close)

    def change_repeating(self, _):
        """Включает/выключает повторение напоминания по дням
           и включает/выключает кнопки выбора режима повторения"""
        state = self.repeat_switch.isChecked()
        # state берётся не из аргумента, а определяется в теле функции
        # потому что к этой функции подключаются несколько чекбоксов
        week_buttons_state = self.week_selection_switch.isChecked()
        calendar_button_state = self.calendar_selection_switch.isChecked()
        for button in self.week_buttons:
            button.setEnabled(week_buttons_state and state)
        self.calendar_selection_btn.setEnabled(calendar_button_state and state)
        self.week_selection_switch.setEnabled(state)
        self.calendar_selection_switch.setEnabled(state)

    def enlarge_hours(self):
        value = int(self.hours_label.text())
        if value < 23:
            new_value = str(int(value) + 1).rjust(2, '0')
        else:
            new_value = '00'
        self.hours_label.setText(new_value)

    def reduce_hours(self):
        value = int(self.hours_label.text())
        if value > 0:
            new_value = str(int(value) - 1).rjust(2, '0')
        else:
            new_value = '23'
        self.hours_label.setText(new_value)

    def enlarge_minutes(self):
        value = int(self.minutes_label.text())
        if value < 59:
            new_value = str(int(value) + 1).rjust(2, '0')
        else:
            new_value = '00'
            self.enlarge_hours()
        self.minutes_label.setText(new_value)

    def reduce_minutes(self):
        value = int(self.minutes_label.text())
        if value > 0:
            new_value = str(int(value) - 1).rjust(2, '0')
        else:
            new_value = '59'
            self.reduce_hours()
        self.minutes_label.setText(new_value)

    def select_week_date(self):
        """Включает/выключает повторение напоминания в выбранный день надели"""
        sender = self.sender()
        day_index = self.week_buttons.index(sender)
        stylesheet = '''border: 3px solid;
                        border-radius: 15px;'''

        if self.week_days[day_index]:
            # Если день недели включен, выключаем:
            sender.setStyleSheet(stylesheet + '\nbackground-color: rgb(108, 108, 108);')
            self.week_days[day_index] = False
        else:
            # Если день недели выключен, включаем:
            sender.setStyleSheet(stylesheet + '\nbackground-color: rgb(255, 255, 0);')
            self.week_days[day_index] = True

    def select_calendar_dates(self):
        """Открывает окно для выбора конкретных дат повтора напоминания"""
        self.calendar_dialog = CalendarDialog(self.month_dates)
        self.calendar_dialog.show()

    def apply(self):
        """Применяет изменения"""
        stylesheet_1 = '''border: 2px solid black;
                          border-radius: 10px;'''
        # Стиль поля ввода заголовка
        stylesheet_2 = '''background-color: rgb(255, 255, 255);
                          border: 3px solid black;
                          border-radius: 10px;'''
        # Стиль кнопки выбора дат повторения напоминания
        stylesheet_3 = '''background-color: rgb(255, 255, 0);
                          border: 3px solid black;
                          border-radius: 15px;'''
        # Стиль кнопок выбора дней недели, в которые приходит напоминание
        # Устанавливаем стандартные стили:
        self.title_line.setStyleSheet(stylesheet_1)
        self.calendar_selection_btn.setStyleSheet(stylesheet_2)
        for button, week_day in zip(self.week_buttons, self.week_days):
            if week_day:
                stylesheet_3 = stylesheet_3.replace('(108, 108, 108)', '(255, 255, 0)')
            else:
                stylesheet_3 = stylesheet_3.replace('(255, 255, 0)', '(108, 108, 108)')
            button.setStyleSheet(stylesheet_3)
        # Если поле отсутствует заголовок, подсвечиваем поле ввода красным - так нельзя
        if not self.title_line.text():
            self.title_line.setStyleSheet(stylesheet_1.replace('black', 'red'))
            return
        # Если заголовок слишком длинный, подсвечиваем поле ввода красным - так нельзя
        if QPushButton(self.title_line.text(), self).sizeHint().width() > 180:
            self.title_line.setStyleSheet(stylesheet_1.replace('black', 'red'))
            return
        # Если даты повтора не выбраны, подсвечиваем кнопку выбора дат - так нельзя
        if self.repeat_switch.isChecked() and \
                self.calendar_selection_switch.isChecked() and not self.month_dates:
            self.calendar_selection_btn.setStyleSheet(stylesheet_2.replace('black', 'red'))
            return
        # Если не выбраны дни недели, в которые повторяется напоминание,
        # подсвечиваем соответствующие кнопки - так нельзя
        if self.repeat_switch.isChecked() and not any(self.week_days):
            stylesheet_3 = stylesheet_3.replace('black', 'red')
            for button in self.week_buttons:
                button.setStyleSheet(stylesheet_3)
            return

        # Изменяем параметры напоминания на новые(применяем изменения):
        self.notify.title = self.title_line.text()
        self.notify.text = self.plain_text.toPlainText()
        current_date = dt.datetime.now()
        self.notify.time = dt.datetime(current_date.year, current_date.month,
                                       current_date.day, int(self.hours_label.text()),
                                       int(self.minutes_label.text()))
        self.notify.week_days = self.week_days
        self.notify.month_dates = self.month_dates
        if self.repeat_switch.isChecked():
            if self.week_selection_switch.isChecked():
                self.notify.repeating_mode = 1
            else:
                self.notify.repeating_mode = 2
        else:
            self.notify.repeating_mode = 0
        if self.ringtone_switch.checkState():
            self.notify.song = self.ringtone_selector.currentText()
        else:
            self.notify.song = None
        # Обновляем виджет напоминания:
        window.update_notify_widget(self.notify)
        self.save = True
        self.close()

    def keyPressEvent(self, event):
        # Клавиша enter или сочетание ctrl+S сохраняют изменения, а escape отменяет
        if event.key() == 16777220 or \
                (int(event.modifiers()) == Qt.ControlModifier and event.key() == Qt.Key_S):
            self.apply()
        elif event.key() == 16777216:
            self.close()

    def closeEvent(self, _):
        # Если создавалось новое напоминание, но изменения не были приняты,
        # это напоминание следует удалить:
        if self.is_new and not self.save:
            window.remove_notify(window.notifys_widgets[self.notify])


class CalendarDialog(QWidget):
    def __init__(self, dates):
        super().__init__()
        self.notify_dates = dates  # Уже существующие даты повтора напоминания
        self.dates = dates.copy()  # В этот список будут добавляться новые даты
        uic.loadUi('resources\\ui\\CalendarDialog.ui', self)
        self.initUi()

    def initUi(self):
        icon = QIcon(os.getcwd() + '\\resources\\images\\calendar_dialog_icon.ico')
        self.setWindowIcon(icon)
        self.dates_list.ScrollMode()
        self.calendar_widget.clicked.connect(self.add_date)
        self.dates_list.itemActivated.connect(self.remove_date)
        for date in self.dates:
            self.dates_list.addItem(date.strftime("%d/%m/%Y"))
        self.apply_btn.clicked.connect(self.apply)
        self.cancel_btn.clicked.connect(self.close)

    def add_date(self):
        date = self.calendar_widget.selectedDate().toPyDate()
        if date not in self.dates and date >= dt.date.today():
            self.dates.append(date)
            self.dates_list.addItem(date.strftime("%d/%m/%Y"))

    def remove_date(self, item):
        # Нажатие на уже выбранную дату удаляет её из списка
        date = dt.date(*[int(i) for i in item.text().split('/')][::-1])
        self.dates_list.takeItem(self.dates.index(date))
        self.dates.remove(date)

    def apply(self):
        # В поле экземпляра класса Notification переписываются новые даты:
        self.notify_dates.clear()
        for date in self.dates:
            self.notify_dates.append(date)
        self.close()


class MainWindow(QWidget):
    """Основное окно приложения со списком напоминаний"""

    def __init__(self):
        super().__init__()
        self.activateWindow()
        self.timers = {}  # Таймеры, отсчитывающие время до уведомлений
        self.notifys = load_notifys()  # Список напоминаний
        self.notifys_widgets = {}  # Список виджетов напоминаний
        self.set_timers()
        self.initUI()
        self.show_notifys()
        self.resize_notifys_list()

    def initUI(self):
        icon = QIcon(os.getcwd() + '\\resources\\images\\icon.ico')
        self.setWindowIcon(icon)
        self.setWindowTitle('Noty')
        self.setGeometry(500, 200, 454, 400)
        self.setMinimumWidth(454)
        self.setStyleSheet('''background-image: url(:/images/main_theme.jpg);
                              background-repeat: no-repeat;
                              background-color: rgb(240, 240, 240);
                              ''')
        self.group_box = QGroupBox("Ваши напоминания")
        self.group_box.setStyleSheet('border: none;')
        self.notify_list = QVBoxLayout(self)
        # notify_list - лейаут с виджетами напоминаний(список напоминаний)
        self.notify_list.setSpacing(0)
        self.group_box.setLayout(self.notify_list)
        self.scroll = QScrollArea()
        # Список будет прокручиваемым благодаря QScrollArea
        self.scroll.setWidget(self.group_box)
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet('border: 3px solid black;')
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.scroll)
        self.add_notify_btn = QPushButton('Добавить напоминание', self)
        self.add_notify_btn.setFont(QFont('Arial', 14))
        self.add_notify_btn.clicked.connect(self.add_notify)
        self.add_notify_btn.setFixedWidth(350)
        self.add_notify_btn.setFixedHeight(40)
        self.add_notify_btn.setStyleSheet('''background: none;
                                             background-color: rgb(255, 255, 255);
                                             border: 2px solid;
                                             border-radius: 17px;
                                             ''')
        self.button_layout = QHBoxLayout()
        self.button_layout.addWidget(self.add_notify_btn)
        self.layout.addLayout(self.button_layout)  # Чтобы кнопка всегда находилась по центру

    def resize_notifys_list(self):
        # При любом изменении списка уведомлений высота списка должна корректироваться,
        # иначе будут изменяться пропорции виджетов напоминаний
        self.group_box.setFixedHeight(int(len(self.notifys) * 63.36 + 40))

    def show_notifys(self):
        """Отрисовывает все напоминания"""
        for index, notify in enumerate(self.notifys):
            notify_widget = NotifyWidget(notify, self)
            self.notifys_widgets[notify] = notify_widget
            self.notify_list.addWidget(notify_widget)

    def add_notify(self):
        # Создаём пустое напоминание:
        new_notify = Notification(dt.datetime.now(), '', '')
        self.notifys.append(new_notify)
        # Создаём виджет для напоминания, но не отображаем его:
        new_notify_widget = NotifyWidget(new_notify, self)
        self.notifys_widgets[new_notify] = new_notify_widget
        # И даём пользователю отредактировать новое напоминание
        # Если пользователь отменит создание, созданное напоминание будет удалено
        new_notify_widget.edit_notify(new_notify=True)
        # new_notify=True говорит о том что редактируется новое напоминание,
        # и при отмене редактирования его следует удалить

    def remove_notify(self, notify_widget):
        notify = notify_widget.notify
        # Удаляем напоминание:
        self.notifys.remove(notify)
        # Удаляем виджет:
        notify_widget.close()
        del self.notifys_widgets[notify]
        self.notify_list.removeWidget(notify_widget)
        # Удаляем таймер:
        timer = self.timers.get(notify)
        if timer is not None:
            if timer.isActive():
                timer.stop()
            del timer
        self.resize_notifys_list()

    def update_notify_widget(self, notify):
        """Переписывает заголовок и время напоминания"""
        widget = self.notifys_widgets[notify]
        widget.time_label.setText(notify.time.strftime('%H:%M'))
        widget.title_label.setText(notify.title)
        # Если виджет только создан и ещё не отображён, то он отображается:
        if widget.visibleRegion().isEmpty():
            self.notify_list.addWidget(widget)
        self.set_timer(notify)
        self.resize_notifys_list()

    def set_timer(self, notify):
        """Запускает/останавливает таймер до напоминания"""
        timer = self.timers.get(notify)
        try:
            interval = notify.next_time() - dt.datetime.now()
            if timer is not None and timer.isActive():
                timer.stop()
            else:
                timer = QTimer()
                self.timers[notify] = timer
                timer.timeout.connect(partial(self.timeout, notify))
            timer.setInterval(int(interval.total_seconds() * 1000))
            timer.start()
        except NotificationError:
            if timer is not None and timer.isActive():
                timer.stop()

    def set_timers(self):
        """Устанавливает таймеры на все напоминания"""
        for notify in self.notifys:
            self.set_timer(notify)

    def timeout(self, notify):
        """Присылает напоминание"""
        notify.notify()
        self.timers[notify].stop()

    def save_notifys(self):
        """Сохраняет данные о всех напоминаниях в базу данных"""
        connection = sqlite3.connect('database\\notifications_db.db')
        # Удалим все напоминания и запишем по новой:
        cursor = connection.cursor()
        cursor.execute('DELETE FROM notifications')
        for id_, notify in enumerate(self.notifys):
            cursor.execute('''INSERT INTO notifications
                              (id, datetime, title, text, included, repeating_mode, song)
                              VALUES
                              (?, ?, ?, ?, ?, ?, ?)''',
                           (id_, notify.time, notify.title, notify.text,
                            notify.included, notify.repeating_mode, notify.song))
        connection.commit()
        connection.close()

        # Сохранение атрибутов напоминаний, являющихся массивами, в json файлы,
        # т. к. одной ячейки таблицы не хватит для записи массива:
        with open('database\\week_days.json', 'w', encoding='utf-8') as json_file:
            week_days = {id_: notify.week_days for id_, notify in enumerate(self.notifys)}
            json_file.write(json.dumps(week_days, indent=2))
        with open('database\\month_dates.json', 'w', encoding='utf-8') as json_file:
            month_dates = {id_: notify.month_dates for id_, notify in enumerate(self.notifys)}
            for id_, dates in month_dates.items():
                month_dates[id_] = [f'{date.year}/{date.month}/{date.day}' for date in dates]
            json_file.write(json.dumps(month_dates, indent=2))

    def resizeEvent(self, e):
        self.resize_notifys_list()

    def closeEvent(self, e):
        self.hide()
        # В файл state.txt записывается closed, чтобы модуль приложения,
        # отвечающий за фоновую работу, понимал что основной модуль закрыт
        # и программа должна работать в фоне
        with open('state.txt', 'w') as state_file:
            state_file.write('closed')
        self.save_notifys()
        # Запуск форового модуля:
        subprocess.Popen('background_working')


def load_notifys():
    """Загружает напоминания из базы данных sqlite и json файлов"""
    # Сначала подгружаем только те атрибуты напоминаний,
    # которые представлены списками и хранятся в json файлах:
    with open('database\\week_days.json', 'r', encoding='utf-8') as json_file:
        try:
            data = json.loads(json_file.read())
        except json.JSONDecodeError:
            data = {}
        week_days = {}
        for id_, days in data.items():
            week_days[int(id_)] = days
    with open('database\\month_dates.json', 'r', encoding='utf-8') as json_file:
        try:
            data = json.loads(json_file.read())
        except json.JSONDecodeError:
            data = {}
        month_dates = {}
        for id_, dates in data.items():
            dates = [dt.datetime.strptime(date, '%Y/%m/%d').date() for date in dates]
            month_dates[int(id_)] = dates
    # week_days и month_days - словари, где ключи это id напоминаний,
    # а значения - списки с соответствующими данными

    # Загружаем все остальные данные из БД:
    connection = sqlite3.connect('database\\notifications_db.db')
    cursor = connection.cursor()
    data = cursor.execute('SELECT * FROM notifications').fetchall()
    connection.close()
    # Приводим к необходимому формату и создаём объекты напоминаний:
    data = [list(row) for row in data]
    notifications = []
    for row in data:
        row[1] = dt.datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S')
        row[2] = str(row[2])
        row[3] = str(row[3])
        row[4] = bool(row[4])
        row.insert(5, week_days[row[0]])
        row.insert(6, month_dates[row[0]])
        notifications.append(Notification(*row[1:]))
    return notifications


if __name__ == '__main__':
    with open('state.txt', 'w') as f:
        f.write('working')
    # В файл state.txt записывается working, чтобы модуль приложения,
    # отвечающий за фоновую работу, понимал что основной модуль открыт
    # и нужно прекращать свою работу
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
