# login_window.py
from PyQt5.QtWidgets import QMainWindow
from PyQt5.uic import loadUi
from settings_window import SettingsWindow

class LoginWindow(QMainWindow):
    def __init__(self):
        super(LoginWindow, self).__init__()
        loadUi('UI/login_window.ui', self)

        self.register_button.clicked.connect(self.go_to_register_page)
        self.login_button.clicked.connect(self.open_settings_window)

        self.show()

    def go_to_register_page(self):
        print("Go TO Register Page")

    def open_settings_window(self):
        self.settings_window = SettingsWindow()
        self.settings_window.displayInfo()
        self.close()