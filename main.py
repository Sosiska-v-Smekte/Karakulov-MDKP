import sys
import bcrypt
from PySide6.QtWidgets import QApplication

from core.database import init_db, SessionLocal
from core.models import Employee
from gui.login_window import LoginWindow
from gui.base_window import BaseWindow
from gui.head_window import HeadWorkspace
from gui.teacher_window import TeacherWorkspace
from gui.acc_window import AccountantWorkspace


def create_admin_if_not_exists():
    """
    Автоматически создает начальную учетную запись Заведующего кафедрой,
    если база данных запускается впервые и в ней нет сотрудников.
    """
    db = SessionLocal()
    try:
        if db.query(Employee).count() == 0:
            salt = bcrypt.gensalt()
            # Хешируем безопасный пароль по умолчанию
            hashed_pw = bcrypt.hashpw(b"admin", salt).decode('utf-8')

            admin = Employee(
                last_name="Каракулов",
                first_name="Александр",
                middle_name="Алексеевич",
                role="head",
                login="admin",
                password_hash=hashed_pw,
                email="admin@ikit.sfu-kras.ru",
                phone="+7 (999) 123-45-67",
                is_active=True
            )
            db.add(admin)
            db.commit()
            print("[БД] Администратор по умолчанию успешно создан (Логин: admin, Пароль: admin)")
    except Exception as e:
        db.rollback()
        print(f"[Ошибка] Не удалось создать администратора по умолчанию: {e}")
    finally:
        db.close()


class ApplicationController:
    """Основной контроллер жизненного цикла и навигации приложения"""

    def __init__(self):
        self.login_win = None
        self.main_win = None

    def start(self):
        """Запуск стартового окна авторизации"""
        self.login_win = LoginWindow()
        # Подключаем сигнал успешного входа к методу открытия главного интерфейса
        self.login_win.login_successful.connect(self.show_main_window)
        self.login_win.show()

    def show_main_window(self, user):
        """
        Метод-роутер. Закрывает окно входа, создает базовую оболочку приложения
        и динамически подгружает в нее рабочую область под конкретную роль.
        """
        self.main_win = BaseWindow(user)

        # Маршрутизация интерфейсов на основе ролей из базы данных
        if user.role == 'head':
            workspace_widget = HeadWorkspace(user)
        elif user.role in ['teacher', 'uvp']:
            # Преподаватели и УВП используют идентичную логику двух вкладок (задачи и отчеты)
            workspace_widget = TeacherWorkspace(user)
        elif user.role == 'accountant':
            workspace_widget = AccountantWorkspace(user)
        else:
            # Резервный вариант на случай непредвиденной роли
            workspace_widget = TeacherWorkspace(user)

        # Интегрируем кастомный интерфейс роли в QStackedWidget базового окна
        self.main_win.workspace.addWidget(workspace_widget)
        self.main_win.workspace.setCurrentWidget(workspace_widget)

        # Отображаем полностью собранное приложение
        self.main_win.show()


if __name__ == "__main__":
    # 1. Создаем файлы и таблицы базы данных SQLite, если они отсутствуют
    init_db()

    # 2. Проверяем наличие учетных записей и добавляем тестового заведующего
    create_admin_if_not_exists()

    # 3. Инициализируем графическую систему PySide6
    app = QApplication(sys.argv)

    # Задаем чистый и современный кроссплатформенный стиль интерфейса
    app.setStyle("Fusion")

    # 4. Передаем управление контроллеру и запускаем цикл обработки событий
    controller = ApplicationController()
    controller.start()

    sys.exit(app.exec())