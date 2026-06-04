import os
import shutil
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QScrollArea, QTabWidget, QDialog, QFileDialog, QMessageBox, QFrame
)
from PySide6.QtCore import Qt
from core.database import SessionLocal
from core.models import Work, WorkTeam


class TeacherTaskCard(QFrame):
    """Карточка задачи для списка преподавателя"""

    def __init__(self, team_record, mode, click_callback):
        super().__init__()
        self.team_record_id = team_record.id
        self.mode = mode
        self.click_callback = click_callback

        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(80)

        layout = QHBoxLayout(self)

        info_layout = QVBoxLayout()
        title = QLabel(f"<b>{team_record.work.title}</b>")
        deadline = QLabel(
            f"Дедлайн: {team_record.work.end_date.strftime('%d.%m.%Y') if team_record.work.end_date else 'Не указан'}")
        info_layout.addWidget(title)
        info_layout.addWidget(deadline)
        layout.addLayout(info_layout)

        # Индикация статуса
        status_label = QLabel()
        status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        if team_record.task_status == 'Выполнено':
            status_label.setText("Отправлено на проверку")
            self.setStyleSheet("background-color: #d4edda; color: black; border: 1px solid #c3e6cb; border-radius: 5px;")
        elif self.mode == 'todo':
            status_label.setText("Новая задача")
            self.setStyleSheet("background-color: #e3f2fd; color: black; border: 1px solid #b6d4fe; border-radius: 5px;")  # Голубой
        else:
            status_label.setText("В работе")
            self.setStyleSheet("background-color: #fff3cd; color: black; border: 1px solid #ffeeba; border-radius: 5px;")  # Желтый

        layout.addWidget(status_label)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.click_callback(self.team_record_id, self.mode)


class TeacherTaskDialog(QDialog):
    """Модальное окно просмотра задачи, принятия в работу и прикрепления файлов"""

    def __init__(self, team_record_id, mode):
        super().__init__()
        self.team_record_id = team_record_id
        self.mode = mode  # 'todo' или 'inprogress'
        self.db = SessionLocal()
        self.selected_file_path = None

        self.setWindowTitle("Информация о работе")
        self.setMinimumSize(450, 400)

        self.setup_ui()

    def setup_ui(self):
        # Подтягиваем данные из БД
        self.team_record = self.db.query(WorkTeam).get(self.team_record_id)
        work = self.team_record.work

        layout = QVBoxLayout(self)

        # Информационный блок
        layout.addWidget(QLabel(f"<h3>{work.title}</h3>"))

        desc_label = QLabel(f"<b>Описание:</b><br>{work.description}")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        layout.addWidget(QLabel(f"<b>Постановщик:</b> {work.author.last_name} {work.author.first_name}"))
        layout.addWidget(QLabel(f"<b>Дедлайн:</b> {work.end_date}"))
        layout.addWidget(QLabel(f"<b>Ожидаемая выплата:</b> {self.team_record.amount_to_pay} руб."))

        layout.addStretch()

        # Разная логика кнопок в зависимости от вкладки
        if self.mode == 'todo':
            btn_accept = QPushButton("Принять к исполнению")
            btn_accept.setStyleSheet("background-color: #2196F3; color: white; height: 35px; font-weight: bold;")
            btn_accept.clicked.connect(self.accept_task)
            layout.addWidget(btn_accept)

        elif self.mode == 'inprogress':
            # Блок работы с файлом
            file_layout = QHBoxLayout()
            self.file_label = QLabel("Файл не выбран")
            btn_attach = QPushButton("Прикрепить отчет")
            btn_attach.clicked.connect(self.attach_file)

            file_layout.addWidget(self.file_label)
            file_layout.addWidget(btn_attach)
            layout.addLayout(file_layout)

            btn_submit = QPushButton("Завершить и отправить")
            btn_submit.setStyleSheet("background-color: #4CAF50; color: white; height: 35px; font-weight: bold;")
            btn_submit.clicked.connect(self.submit_task)
            layout.addWidget(btn_submit)

    def accept_task(self):
        """Переводит задачу во вкладку 'В работе'"""
        self.team_record.task_status = 'В работе'
        self.db.commit()
        self.accept()

    def attach_file(self):
        """Открывает проводник для выбора документа"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите файл отчета", "",
                                                   "All Files (*);;PDF (*.pdf);;Word (*.docx)")
        if file_path:
            self.selected_file_path = file_path
            self.file_label.setText(os.path.basename(file_path))

    def submit_task(self):
        """Сохраняет файл и переводит статус на проверку Заведующему"""
        if self.selected_file_path:
            # Создаем папку для отчетов, если её нет
            upload_dir = "uploads/reports"
            os.makedirs(upload_dir, exist_ok=True)

            # Копируем файл в рабочую директорию проекта
            filename = os.path.basename(self.selected_file_path)
            # Добавим ID записи, чтобы файлы с одинаковыми именами не перезаписывались
            safe_filename = f"task_{self.team_record.id}_{filename}"
            dest_path = os.path.join(upload_dir, safe_filename)

            shutil.copy(self.selected_file_path, dest_path)
            self.team_record.report_file_path = dest_path

        self.team_record.task_status = 'Выполнено'

        # Если все участники завершили свою часть, можно автоматически
        # поменять статус самой задачи (Work) на 'На проверке'
        all_completed = all(member.task_status == 'Выполнено' for member in self.team_record.work.team_members)
        if all_completed:
            self.team_record.work.status = 'На проверке'

        self.db.commit()
        self.accept()

    def closeEvent(self, event):
        self.db.close()


class TeacherWorkspace(QWidget):
    """Главный виджет рабочего пространства Преподавателя / УВП"""

    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.db = SessionLocal()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Вкладка 1: Для выполнения
        self.tab_todo = QWidget()
        self.setup_todo_tab()
        self.tabs.addTab(self.tab_todo, "Мои работы для выполнения")

        # Вкладка 2: Для отправления (В работе)
        self.tab_inprogress = QWidget()
        self.setup_inprogress_tab()
        self.tabs.addTab(self.tab_inprogress, "Мои работы для отправления")

    def setup_todo_tab(self):
        layout = QVBoxLayout(self.tab_todo)

        btn_refresh = QPushButton("Обновить список задач")
        btn_refresh.clicked.connect(self.load_data)
        layout.addWidget(btn_refresh, alignment=Qt.AlignRight)

        self.todo_scroll = QScrollArea()
        self.todo_scroll.setWidgetResizable(True)
        self.todo_container = QWidget()
        self.todo_layout = QVBoxLayout(self.todo_container)
        self.todo_layout.setAlignment(Qt.AlignTop)
        self.todo_scroll.setWidget(self.todo_container)

        layout.addWidget(self.todo_scroll)

    def setup_inprogress_tab(self):
        layout = QVBoxLayout(self.tab_inprogress)

        btn_refresh = QPushButton("Обновить список")
        btn_refresh.clicked.connect(self.load_data)
        layout.addWidget(btn_refresh, alignment=Qt.AlignRight)

        self.inprog_scroll = QScrollArea()
        self.inprog_scroll.setWidgetResizable(True)
        self.inprog_container = QWidget()
        self.inprog_layout = QVBoxLayout(self.inprog_container)
        self.inprog_layout.setAlignment(Qt.AlignTop)
        self.inprog_scroll.setWidget(self.inprog_container)

        layout.addWidget(self.inprog_scroll)

        self.load_data()  # Первичная загрузка при открытии

    def clear_layout(self, layout):
        for i in reversed(range(layout.count())):
            widget = layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)

    def load_data(self):
        """Запрашивает из БД задачи и распределяет их по двум вкладкам"""
        self.clear_layout(self.todo_layout)
        self.clear_layout(self.inprog_layout)

        # Получаем все назначения для текущего пользователя
        my_tasks = self.db.query(WorkTeam).filter(
            WorkTeam.employee_id == self.current_user.id
        ).all()

        for task in my_tasks:
            # Если задача уже закрыта заведующим, не показываем её в активных
            if task.work.status in ['Завершена', 'Отменена']:
                continue

            if task.task_status == 'Назначен':
                card = TeacherTaskCard(task, 'todo', self.open_dialog)
                self.todo_layout.addWidget(card)
            elif task.task_status == 'В работе':
                card = TeacherTaskCard(task, 'inprogress', self.open_dialog)
                self.inprog_layout.addWidget(card)
            elif task.task_status == 'Выполнено':
                # Можно выводить завершенные, но ожидающие проверки карточки
                # зелёным цветом в самом низу вкладки "В работе" для наглядности
                card = TeacherTaskCard(task, 'inprogress', self.open_dialog)
                card.setEnabled(False)  # Блокируем клик, чтобы не отправить дважды
                self.inprog_layout.addWidget(card)

    def open_dialog(self, team_record_id, mode):
        dialog = TeacherTaskDialog(team_record_id, mode)
        if dialog.exec():
            self.load_data()  # Обновляем списки после "Принять" или "Отправить"
