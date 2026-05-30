from datetime import date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QScrollArea, QFrame, QTabWidget, QDialog, QLineEdit,
    QTextEdit, QComboBox, QDateEdit, QMessageBox, QCompleter,
    QListWidget, QFileDialog
)
from PySide6.QtCore import Qt, QDate
from core.database import SessionLocal
from core.models import Work, Employee, WorkType, WorkTeam


class WorkCard(QFrame):
    """Виджет для отображения краткой информации о работе в списке"""

    def __init__(self, work, click_callback):
        super().__init__()
        self.work_id = work.id
        self.click_callback = click_callback

        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(80)

        layout = QHBoxLayout(self)

        # Название и ответственный
        info_layout = QVBoxLayout()
        title = QLabel(f"<b>{work.title}</b>")
        resp_name = f"{work.responsible.last_name} {work.responsible.first_name[0]}." if work.responsible else "Не назначен"
        responsible = QLabel(f"Ответственный: {resp_name}")
        info_layout.addWidget(title)
        info_layout.addWidget(responsible)
        layout.addLayout(info_layout)

        # Статус
        status_label = QLabel(work.status)
        status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(status_label)

        # Цветовая индикация
        today = date.today()
        if work.status == 'Завершена':
            self.setStyleSheet("background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 5px;")  # Зеленый
        elif work.end_date and work.end_date < today and work.status != 'Завершена':
            self.setStyleSheet("background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 5px;")  # Красный
        else:
            self.setStyleSheet("background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 5px;")  # Серый

    def mousePressEvent(self, event):
        """Обработка клика по карточке для открытия подробностей"""
        if event.button() == Qt.LeftButton:
            self.click_callback(self.work_id)


class WorkDialog(QDialog):
    """Модальное окно создания и редактирования работы"""

    def __init__(self, work_id=None, current_user_id=None):
        super().__init__()
        self.work_id = work_id
        self.current_user_id = current_user_id
        self.db = SessionLocal()

        title_text = "Редактирование работы" if work_id else "Создание работы"
        self.setWindowTitle(title_text)
        self.setMinimumSize(500, 600)

        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Название
        layout.addWidget(QLabel("Название работы:"))
        self.title_input = QLineEdit()
        layout.addWidget(self.title_input)

        # Описание
        layout.addWidget(QLabel("Описание:"))
        self.desc_input = QTextEdit()
        self.desc_input.setFixedHeight(100)
        layout.addWidget(self.desc_input)

        # Тип работы (Классификатор)
        layout.addWidget(QLabel("Тип работы (классификация):"))
        self.type_combo = QComboBox()
        layout.addWidget(self.type_combo)

        # Главный ответственный (с поиском)
        layout.addWidget(QLabel("Ответственный:"))
        self.resp_combo = QComboBox()
        self.resp_combo.setEditable(True)  # Включаем возможность ввода для поиска
        layout.addWidget(self.resp_combo)

        # Дополнительные исполнители
        layout.addWidget(QLabel("Дополнительные исполнители:"))
        team_layout = QHBoxLayout()
        self.team_combo = QComboBox()
        self.team_combo.setEditable(True)
        btn_add_team = QPushButton("+ Добавить")
        btn_add_team.clicked.connect(self.add_team_member)
        team_layout.addWidget(self.team_combo)
        team_layout.addWidget(btn_add_team)
        layout.addLayout(team_layout)

        self.team_list = QListWidget()
        self.team_list.setFixedHeight(80)
        layout.addWidget(self.team_list)

        # Срок выполнения
        layout.addWidget(QLabel("Срок выполнения (Дедлайн):"))
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate().addDays(7))
        layout.addWidget(self.date_input)

        # Статус
        layout.addWidget(QLabel("Статус:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(['Запланирована', 'В работе', 'На проверке', 'Завершена', 'Отменена'])
        layout.addWidget(self.status_combo)

        # Кнопки управления
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Сохранить изменения")
        self.btn_save.setStyleSheet("background-color: #4CAF50; color: white;")
        self.btn_save.clicked.connect(self.save_work)

        self.btn_delete = QPushButton("Удалить работу")
        self.btn_delete.setStyleSheet("background-color: #f44336; color: white;")
        self.btn_delete.clicked.connect(self.delete_work)
        if not self.work_id:
            self.btn_delete.hide()

        btn_layout.addWidget(self.btn_delete)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    def load_data(self):
        """Загрузка списков сотрудников, типов работ и данных текущей задачи"""
        # Загружаем типы работ
        types = self.db.query(WorkType).all()
        for wt in types:
            self.type_combo.addItem(f"{wt.name} ({wt.base_cost} руб.)", wt.id)

        # Загружаем сотрудников для поиска
        employees = self.db.query(Employee).filter(Employee.role.in_(['teacher', 'uvp'])).all()
        emp_names = []
        for emp in employees:
            name = f"{emp.last_name} {emp.first_name} ({emp.id})"
            emp_names.append(name)
            self.resp_combo.addItem(name, emp.id)
            self.team_combo.addItem(name, emp.id)

        # Настраиваем автодополнение для поиска
        completer = QCompleter(emp_names)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.resp_combo.setCompleter(completer)
        self.team_combo.setCompleter(completer)

        # Если редактирование - подтягиваем данные
        if self.work_id:
            work = self.db.query(Work).get(self.work_id)
            self.title_input.setText(work.title)
            self.desc_input.setText(work.description)
            self.status_combo.setCurrentText(work.status)
            if work.end_date:
                self.date_input.setDate(work.end_date)

            # TODO: Установить индексы комбобоксов и загрузить команду из WorkTeam

    def add_team_member(self):
        member = self.team_combo.currentText()
        if member:
            self.team_list.addItem(member)

    def save_work(self):
        # TODO: Извлечь данные, создать/обновить объект Work, обновить WorkTeam
        # Если статус меняется на 'Завершена', система готова передать данные бухгалтеру
        self.db.commit()
        self.accept()  # Закрывает диалог с кодом успеха

    def delete_work(self):
        # Удаление работы из БД
        self.accept()

    def closeEvent(self, event):
        self.db.close()


class HeadWorkspace(QWidget):
    """Главный виджет рабочего пространства Заведующего"""

    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.db = SessionLocal()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Вкладки
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Вкладка 1: Создание и контроль работы
        self.tab_control = QWidget()
        self.setup_control_tab()
        self.tabs.addTab(self.tab_control, "Создание и контроль работы")

        # Вкладка 2: Выполненные работы
        self.tab_review = QWidget()
        self.setup_review_tab()
        self.tabs.addTab(self.tab_review, "Выполненные работы")

    def setup_control_tab(self):
        layout = QVBoxLayout(self.tab_control)

        # Верхняя панель управления
        toolbar = QHBoxLayout()
        btn_create = QPushButton("+ Создать работу")
        btn_create.setStyleSheet("background-color: #2196F3; color: white; padding: 8px;")
        btn_create.clicked.connect(self.open_work_dialog)

        btn_refresh = QPushButton("Обновить список")
        btn_refresh.clicked.connect(self.load_works)

        toolbar.addWidget(btn_create)
        toolbar.addStretch()
        toolbar.addWidget(btn_refresh)
        layout.addLayout(toolbar)

        # Список работ (Scroll Area)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.works_container = QWidget()
        self.works_layout = QVBoxLayout(self.works_container)
        self.works_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.works_container)

        layout.addWidget(self.scroll_area)
        self.load_works()

    def setup_review_tab(self):
        """Вкладка с работами, ожидающими проверки файлов"""
        layout = QVBoxLayout(self.tab_review)
        btn_refresh = QPushButton("Обновить список на проверку")
        layout.addWidget(btn_refresh)
        # TODO: Добавить аналогичный список, фильтрующий работы со статусом "На проверке"

    def load_works(self):
        """Загрузка работ из базы и отрисовка карточек"""
        # Очищаем старые карточки
        for i in reversed(range(self.works_layout.count())):
            widget = self.works_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)

        works = self.db.query(Work).all()
        for work in works:
            card = WorkCard(work, self.open_work_dialog)
            self.works_layout.addWidget(card)

    def open_work_dialog(self, work_id=None):
        """Открытие модального окна и обновление списка при сохранении"""
        dialog = WorkDialog(work_id, self.current_user.id)
        if dialog.exec():
            self.load_works()  # Перерисовываем список, если были изменения