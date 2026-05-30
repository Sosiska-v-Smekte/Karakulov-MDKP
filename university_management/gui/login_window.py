import bcrypt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QMessageBox, QHBoxLayout
)
from PySide6.QtCore import Qt, Signal
from core.database import SessionLocal
from core.models import Employee


class LoginWindow(QWidget):
    # Сигнал для передачи объекта пользователя в main.py при успешном входе
    login_successful = Signal(object)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Авторизация")
        self.setFixedSize(350, 400)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(15)

        title = QLabel("Вход в систему")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Выбор роли (ключи совпадают с БД)
        self.role_combo = QComboBox()
        self.role_combo.addItem("Заведующий кафедрой", "head")
        self.role_combo.addItem("Преподаватель", "teacher")
        self.role_combo.addItem("Бухгалтер", "accountant")
        self.role_combo.addItem("УВП", "uvp")
        layout.addWidget(QLabel("Роль:"))
        layout.addWidget(self.role_combo)

        # Логин
        layout.addWidget(QLabel("Логин:"))
        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText("Введите логин")
        layout.addWidget(self.login_input)

        # Пароль
        layout.addWidget(QLabel("Пароль:"))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Введите пароль")
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)

        # Кнопка
        self.btn_login = QPushButton("Войти")
        self.btn_login.setFixedHeight(40)
        self.btn_login.setStyleSheet("""
            QPushButton {
                background-color: #27ae60; color: white; font-weight: bold; border-radius: 5px;
            }
            QPushButton:hover { background-color: #2ecc71; }
        """)
        self.btn_login.clicked.connect(self.authenticate)
        layout.addWidget(self.btn_login)

    def authenticate(self):
        login = self.login_input.text().strip()
        password = self.password_input.text().strip()
        role_code = self.role_combo.currentData()

        if not login or not password:
            QMessageBox.warning(self, "Ошибка", "Поля не могут быть пустыми!")
            return

        db = SessionLocal()
        try:
            # Ищем пользователя в БД
            user = db.query(Employee).filter(
                Employee.login == login,
                Employee.role == role_code
            ).first()

            if user:
                # Проверка хэша пароля
                if bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
                    self.login_successful.emit(user)
                    self.close()
                else:
                    QMessageBox.warning(self, "Ошибка", "Неверный пароль!")
                    self.password_input.clear()
            else:
                QMessageBox.warning(self, "Ошибка", "Пользователь не найден или выбрана неверная роль.")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось подключиться к базе: {e}")
        finally:
            db.close()