from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel
from PyQt5.QtCore import Qt, QUrl, QThread
from PyQt5.QtGui import QFont, QIcon
from PyQt5 import uic, QtMultimedia
from time import sleep
import os
import sys
import ui_resources


class NotifyWindow(QMainWindow):
    def __init__(self, title, text, song):
        super().__init__()
        self.title = title
        self.text = text
        if song != 'None':
            path = os.getcwd() + '\\resources\\audio\\'
            media = QUrl.fromLocalFile(path + song + '.wav')
            self.song = QtMultimedia.QMediaContent(media)
        else:
            self.song = None
        uic.loadUi('resources\\ui\\NotifyWindow.ui', self)
        self.initUi()
        self.play_song()
    
    def initUi(self):
        icon = QIcon(os.getcwd() + '\\resources\\images\\icon.ico')
        self.setWindowIcon(icon)
        self.title_label.setText(self.title)
        width = self.title_label.sizeHint().width() + 20
        if width < 100:
            width = 100
        self.title_label.setFixedWidth(width)
        self.title_label.move((575 - width) / 2, 20)
        self.text_label = QLabel(self.text, self)
        self.text_label.resize(400, 200)
        self.text_label.setStyleSheet('''background: none;
                                         background-color: rgb(255, 255, 255);
                                         border: 2px solid black;
                                         border-radius: 36px;''')
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setFont(QFont('Arial', 14))
        self.scroll_area.setWidget(self.text_label)
        self.postpone_btn.clicked.connect(self.postpone)
        self.close_btn.clicked.connect(self.close)
    
    def play_song(self):
        """Воспроизводит звук уведомления"""
        if self.song is not None:
            # Звук будет воспроизводиться в отдельном потоке
            self.music_thread = MusicThread(self.song)
            self.music_thread.start()
    
    def postpone(self):
        """Откладывает уведомление на выбранный пользователем срок"""
        if self.song is not None:
            self.music_thread.kill()
        self.hide()
        sleep(self.postpone_time_selecter.value() * 60)
        self.show()
        self.play_song()
        self.activateWindow()
    
    def keyPressEvent(self, event):
        # Клавиша enter откладывает уведомление, а escape закрывает
        if event.key() == 16777220:
            self.postpone()
        elif event.key() == 16777216:
            self.close()
    
    def closeEvent(self, e):
        # Необходимо убить поток, воспроизводящий звук, иначе PyQt ругается
        if self.song is not None:
            self.music_thread.kill()


class MusicThread(QThread):
    """Поток для воспроизведения звука оповещения"""
    def __init__(self, song):
        super().__init__()
        self.player = QtMultimedia.QMediaPlayer()
        self.player.setMedia(song)
    
    def run(self):
        self.player.play()
        sleep(5)
    
    def kill(self):
        self.player.stop()


def parse_cmd_args(args):
    """Функция для парсинга аргументов командной строки"""
    return [arg.split('=')[1] for arg in args[1:]]


if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Данный модуль может запускаться исключительно другим
    # модулем приложения(не пользователем), с помощью subprocess.Popen().
    # Заголовок, текст и звук уведомления передаются как аргументы командной строки
    notify_window = NotifyWindow(*parse_cmd_args(sys.argv))
    notify_window.show()
    notify_window.activateWindow()
    sys.exit(app.exec_())
