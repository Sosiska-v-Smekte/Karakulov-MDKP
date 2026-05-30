import sys
import bcrypt
from PySide6.QtWidgets import QApplication

from core.database import init_db, SessionLocal
from core.models import Employee, WorkType
from gui.login_window import LoginWindow
from gui.base_window import BaseWindow
from gui.head_window import HeadWorkspace
from gui.teacher_window import TeacherWorkspace
from gui.acc_window import AccountantWorkspace


def create_admin_if_not_exists():
    """
    Автоматически наполняет базу данных всеми необходимыми начальными данными,
    если система запускается впервые и таблица сотрудников пуста.
    Создает аккаунты для всех ролей и базовые тарифы в классификаторе.
    """
    db = SessionLocal()
    try:
        if db.query(Employee).count() == 0:
            salt = bcrypt.gensalt()

            # Генерация хешей паролей для тестовых учетных записей
            pw_admin = bcrypt.hashpw(b"admin", salt).decode('utf-8')
            pw_t1 = bcrypt.hashpw(b"t1", salt).decode('utf-8')
            pw_t2 = bcrypt.hashpw(b"t2", salt).decode('utf-8')
            pw_t3 = bcrypt.hashpw(b"t3", salt).decode('utf-8')
            pw_u1 = bcrypt.hashpw(b"u1", salt).decode('utf-8')
            pw_u2 = bcrypt.hashpw(b"u2", salt).decode('utf-8')
            pw_acc = bcrypt.hashpw(b"acc", salt).decode('utf-8')

            # Создание штата сотрудников кафедры
            users = [
                # Руководство
                Employee(
                    last_name="Каракулов", first_name="Александр", middle_name="Алексеевич",
                    role="head", login="admin", password_hash=pw_admin,
                    email="karakulov@ikit.sfu-kras.ru", phone="+7 (999) 123-45-67", is_active=True
                ),
                # Профессорско-преподавательский состав (ППС)
                Employee(
                    last_name="Иванов", first_name="Иван", middle_name="Иванович",
                    role="teacher", login="t1", password_hash=pw_t1,
                    email="ivanov@ikit.sfu-kras.ru", phone="+7 (902) 111-22-33", is_active=True
                ),
                Employee(
                    last_name="Петров", first_name="Сергей", middle_name="Петрович",
                    role="teacher", login="t2", password_hash=pw_t2,
                    email="petrov@ikit.sfu-kras.ru", phone="+7 (902) 444-55-66", is_active=True
                ),
                Employee(
                    last_name="Сидорова", first_name="Анна", middle_name="Михайловна",
                    role="teacher", login="t3", password_hash=pw_t3,
                    email="sidorova@ikit.sfu-kras.ru", phone="+7 (902) 777-88-99", is_active=True
                ),
                # Учебно-вспомогательный персонал (УВП)
                Employee(
                    last_name="Смирнов", first_name="Алексей", middle_name="Николаевич",
                    role="uvp", login="u1", password_hash=pw_u1,
                    email="smirnov@ikit.sfu-kras.ru", phone="+7 (913) 123-00-11", is_active=True
                ),
                Employee(
                    last_name="Кузнецова", first_name="Елена", middle_name="Васильевна",
                    role="uvp", login="u2", password_hash=pw_u2,
                    email="kuznecova@ikit.sfu-kras.ru", phone="+7 (913) 456-00-22", is_active=True
                ),
                # Финансовый отдел
                Employee(
                    last_name="Соколова", first_name="Мария", middle_name="Дмитриевна",
                    role="accountant", login="acc", password_hash=pw_acc,
                    email="sokolova@ikit.sfu-kras.ru", phone="+7 (391) 206-22-22", is_active=True
                )
            ]
            db.add_all(users)

            # Первоначальное наполнение классификатора видов работ и базовых ставок
            work_types = [
                WorkType(name="Разработка учебно-методического пособия", base_cost=5000.00, unit="шт", is_active=True),
                WorkType(name="Модернизация и настройка лабораторных стендов", base_cost=3500.00, unit="ауд",
                         is_active=True),
                WorkType(name="Проведение дополнительных консультаций перед ГИА", base_cost=1500.00, unit="час",
                         is_active=True),
                WorkType(name="Технический аудит компьютерной техники кафедры", base_cost=2000.00, unit="компл",
                         is_active=True),
                WorkType(name="Тиражирование и подготовка раздаточных материалов", base_cost=1000.00, unit="заказ",
                         is_active=True)
            ]
            db.add_all(work_types)

            db.commit()
            print("[БД] Инициализация выполнена успешно. Все тестовые учетные записи созданы.")
    except Exception as e:
        db.rollback()
        print(f"[Ошибка БД] Критический сбой при наполнении таблиц: {e}")
    finally:
        db.close()


class ApplicationController:
    """Главный управляющий контроллер для роутинга окон и сессий пользователей"""

    def __init__(self):
        self.login_win = None
        self.main_win = None

    def start(self):
        """Отрисовка стартового окна авторизации приложения"""
        self.login_win = LoginWindow()
        self.login_win.login_successful.connect(self.show_main_window)
        self.login_win.show()

    def show_main_window(self, user):
        """
        Перехватывает сигнал успешной аутентификации, закрывает окно входа,
        создает основную рамку графического интерфейса и внедряет в нее
        рабочую область, соответствующую роли сотрудника.
        """
        self.main_win = BaseWindow(user)

        # Подключаем обработчик на событие уничтожения (закрытия) главного окна,
        # чтобы вернуть окно логина при выходе из аккаунта
        self.main_win.destroyed.connect(self.handle_window_destruction)

        # Динамическое определение рабочего пространства на основе роли из БД
        if user.role == 'head':
            workspace_widget = HeadWorkspace(user)
        elif user.role in ['teacher', 'uvp']:
            # Преподаватели и учебно-вспомогательный персонал используют
            # унифицированный интерфейс двух вкладок (задачи и отправка отчетов)
            workspace_widget = TeacherWorkspace(user)
        elif user.role == 'accountant':
            workspace_widget = AccountantWorkspace(user)
        else:
            workspace_widget = TeacherWorkspace(user)

        # Монтируем рабочую область в QStackedWidget базового окна
        self.main_win.workspace.addWidget(workspace_widget)
        self.main_win.workspace.setCurrentWidget(workspace_widget)

        # Показываем полностью собранное приложение пользователю
        self.main_win.show()

    def handle_window_destruction(self):
        """
        Срабатывает автоматически, когда главное окно закрывается через профиль
        по кнопке 'Выйти из аккаунта'. Сбрасывает ссылки и возвращает форму входа.
        """
        self.main_win = None
        self.start()


if __name__ == "__main__":
    # 1. Проверяем наличие файла базы данных SQLite и генерируем таблицы при отсутствии
    init_db()

    # 2. Наполняем систему администратором, преподавателями, УВП и тарифами
    create_admin_if_not_exists()

    # 3. Инициализация графического ядра PySide6
    app = QApplication(sys.argv)

    # Установка единой аккуратной темы оформления интерфейса
    app.setStyle("Fusion")

    # 4. Запуск контроллера и передача управления бесконечному циклу событий Qt
    controller = ApplicationController()
    controller.start()

    sys.exit(app.exec())