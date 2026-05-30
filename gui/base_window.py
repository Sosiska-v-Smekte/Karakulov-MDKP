from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from core.models import Employee


class BaseWindow(QMainWindow):
    def __init__(self, current_user: Employee):
        super().__init__()
        self.current_user = current_user
        self.setWindowTitle("Информационная система кафедры — ИКИТ (КИ24-06Б)")
        self.setMinimumSize(1024, 768)

        # Главный виджет и layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.setup_header()
        self.setup_workspace()

    def setup_header(self):
        """Создает верхнюю панель с профилем пользователя"""
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #2c3e50; color: white;")
        header_frame.setFixedHeight(60)
        header_layout = QHBoxLayout(header_frame)

        # Логотип или название системы слева
        logo_label = QLabel("Управление дополнительными работами")
        logo_label.setStyleSheet("font-size: 16px; font-weight: bold; padding-left: 15px;")
        header_layout.addWidget(logo_label)

        header_layout.addStretch()

        # --- Универсальный профиль (справа) ---

        # ФИО и Роль
        user_info_label = QLabel(
            f"{self.current_user.last_name} {self.current_user.first_name}\n"
            f"({self.get_role_name()})"
        )
        user_info_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header_layout.addWidget(user_info_label)

        # Аватар (Заглушка)
        avatar_label = QLabel()
        avatar_label.setFixedSize(40, 40)
        avatar_label.setStyleSheet("background-color: #bdc3c7; border-radius: 20px;")
        # Здесь в будущем можно подгружать картинку:
        # avatar_label.setPixmap(QPixmap(self.current_user.avatar_path).scaled(40, 40))
        header_layout.addWidget(avatar_label)

        # Кнопка настроек профиля
        btn_profile = QPushButton("Профиль")
        btn_profile.setCursor(Qt.PointingHandCursor)
        btn_profile.setStyleSheet("background-color: #34495e; border: none; padding: 5px 10px;")
        btn_profile.clicked.connect(self.open_profile_settings)
        header_layout.addWidget(btn_profile)

        # Кнопка выхода
        btn_logout = QPushButton("Выход")
        btn_logout.setCursor(Qt.PointingHandCursor)
        btn_logout.setStyleSheet("background-color: #e74c3c; border: none; padding: 5px 10px;")
        btn_logout.clicked.connect(self.logout)
        header_layout.addWidget(btn_logout)

        self.main_layout.addWidget(header_frame)

    def setup_workspace(self):
        """Место под основной контент (вкладки ролей)"""
        self.workspace = QStackedWidget()
        self.main_layout.addWidget(self.workspace)

    def get_role_name(self):
        roles = {
            "head": "Заведующий",
            "teacher": "Преподаватель",
            "accountant": "Бухгалтер",
            "uvp": "УВП"
        }
        return roles.get(self.current_user.role, "Сотрудник")

    def open_profile_settings(self):
        # TODO: Реализовать модальное окно изменения данных (пароль, email, фото)
        print("Открытие настроек профиля...")

    def logout(self):
        # Закрываем текущее окно и посылаем сигнал о выходе
        self.close()
        # В main.py мы перехватим это событие и снова покажем окно авторизации