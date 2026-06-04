from datetime import date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QScrollArea, QFrame, QTabWidget, QDialog, QLineEdit,
    QTextEdit, QComboBox, QDateEdit, QMessageBox, QCompleter,
    QListWidget
)
from PySide6.QtCore import Qt, QDate, Signal
from core.database import SessionLocal
from core.models import Work, Employee, WorkType, WorkTeam


class ReviewDialog(QDialog):
    def __init__(self, work_id, db_session):
        super().__init__()
        self.work_id = work_id
        self.db = db_session
        self.setWindowTitle("Проверка выполненной работы")
        self.setMinimumSize(400, 300)
        self.setup_ui()

    def setup_ui(self):
        self.work = self.db.query(Work).get(self.work_id)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(f"<h3>Работа: {self.work.title}</h3>"))
        layout.addWidget(QLabel(f"<b>Главный ответственный:</b> {self.work.responsible.last_name}"))

        layout.addWidget(QLabel("<b>Прикрепленные отчеты:</b>"))
        for team_member in self.work.team_members:
            member_name = f"{team_member.employee.last_name} {team_member.employee.first_name[0]}."
            if team_member.report_file_path:
                file_layout = QHBoxLayout()
                file_layout.addWidget(QLabel(f"{member_name}: Файл загружен"))

                btn_download = QPushButton("Скачать / Открыть")
                btn_download.clicked.connect(
                    lambda checked, path=team_member.report_file_path: self.download_file(path))
                file_layout.addWidget(btn_download)
                layout.addLayout(file_layout)
            else:
                layout.addWidget(QLabel(f"{member_name}: Файл не предоставлен"))

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_reject = QPushButton("Вернуть в работу")
        btn_reject.setStyleSheet("background-color: #f44336; color: white;")
        btn_reject.clicked.connect(self.reject_work)

        btn_approve = QPushButton("Утвердить работу (в бухгалтерию)")
        btn_approve.setStyleSheet("background-color: #4CAF50; color: white;")
        btn_approve.clicked.connect(self.approve_work)

        btn_layout.addWidget(btn_reject)
        btn_layout.addWidget(btn_approve)
        layout.addLayout(btn_layout)

    def download_file(self, filepath):
        import os
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl

        abs_path = os.path.abspath(filepath)
        if os.path.exists(abs_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(abs_path))
        else:
            QMessageBox.warning(self, "Ошибка", "Файл не найден на диске!")

    def approve_work(self):
        self.work.status = 'Завершена'
        self.db.commit()
        self.accept()

    def reject_work(self):
        self.work.status = 'В работе'
        for member in self.work.team_members:
            if member.task_status == 'Выполнено':
                member.task_status = 'В работе'
        self.db.commit()
        self.accept()


class WorkCard(QFrame):
    def __init__(self, work, click_callback):
        super().__init__()
        self.work_id = work.id
        self.click_callback = click_callback

        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(80)

        layout = QHBoxLayout(self)

        info_layout = QVBoxLayout()
        title = QLabel(f"<b>{work.title}</b>")
        resp_name = f"{work.responsible.last_name} {work.responsible.first_name[0]}." if work.responsible else "Не назначен"
        responsible = QLabel(f"Ответственный: {resp_name}")
        info_layout.addWidget(title)
        info_layout.addWidget(responsible)
        layout.addLayout(info_layout)

        status_label = QLabel(work.status)
        status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(status_label)

        today = date.today()
        if work.status == 'Завершена':
            self.setStyleSheet("background-color: #d4edda; color: black; border: 1px solid #c3e6cb; border-radius: 5px;")
        elif work.end_date and work.end_date < today and work.status != 'Завершена':
            self.setStyleSheet("background-color: #f8d7da; color: black; border: 1px solid #f5c6cb; border-radius: 5px;")
        else:
            self.setStyleSheet("background-color: #f8f9fa; color: black; border: 1px solid #dee2e6; border-radius: 5px;")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.click_callback(self.work_id)


class WorkDialog(QDialog):
    def __init__(self, work_id=None, current_user_id=None):
        super().__init__()
        self.work_id = work_id
        self.current_user_id = current_user_id
        self.db = SessionLocal()
        self.team_member_ids = []

        title_text = "Редактирование работы" if work_id else "Создание работы"
        self.setWindowTitle(title_text)
        self.setMinimumSize(500, 600)

        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Название работы:"))
        self.title_input = QLineEdit()
        layout.addWidget(self.title_input)

        layout.addWidget(QLabel("Описание:"))
        self.desc_input = QTextEdit()
        self.desc_input.setFixedHeight(100)
        layout.addWidget(self.desc_input)

        layout.addWidget(QLabel("Тип работы (классификация):"))
        self.type_combo = QComboBox()
        layout.addWidget(self.type_combo)

        layout.addWidget(QLabel("Ответственный:"))
        self.resp_combo = QComboBox()
        self.resp_combo.setEditable(True)
        layout.addWidget(self.resp_combo)

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

        layout.addWidget(QLabel("Срок выполнения (Дедлайн):"))
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate().addDays(7))
        layout.addWidget(self.date_input)

        layout.addWidget(QLabel("Статус:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(['Запланирована', 'В работе', 'На проверке', 'Завершена', 'Отменена'])
        layout.addWidget(self.status_combo)

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
        types = self.db.query(WorkType).all()
        for wt in types:
            self.type_combo.addItem(f"{wt.name} ({wt.base_cost} руб.)", wt.id)

        employees = self.db.query(Employee).filter(Employee.role.in_(['teacher', 'uvp'])).all()
        emp_names = []
        for emp in employees:
            name = f"{emp.last_name} {emp.first_name} ({emp.id})"
            emp_names.append(name)
            self.resp_combo.addItem(name, emp.id)
            self.team_combo.addItem(name, emp.id)

        completer = QCompleter(emp_names)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.resp_combo.setCompleter(completer)
        self.team_combo.setCompleter(completer)

        if self.work_id:
            work = self.db.query(Work).get(self.work_id)
            self.title_input.setText(work.title)
            self.desc_input.setText(work.description)
            self.status_combo.setCurrentText(work.status)
            if work.end_date:
                self.date_input.setDate(work.end_date)

    def add_team_member(self):
        member_name = self.team_combo.currentText()
        member_id = self.team_combo.currentData()

        if member_id and member_id not in self.team_member_ids:
            if member_id == self.resp_combo.currentData():
                QMessageBox.warning(self, "Внимание", "Этот сотрудник уже назначен главным ответственным!")
                return
            self.team_member_ids.append(member_id)
            self.team_list.addItem(member_name)

    def save_work(self):
        title = self.title_input.text().strip()
        desc = self.desc_input.toPlainText().strip()
        work_type_id = self.type_combo.currentData()
        resp_id = self.resp_combo.currentData()
        status = self.status_combo.currentText()
        end_date = self.date_input.date().toPython()

        if not title or not work_type_id or not resp_id:
            QMessageBox.warning(self, "Ошибка", "Заполните Название, Тип работы и выберите Ответственного!")
            return

        try:
            wt = self.db.query(WorkType).get(work_type_id)
            base_cost = wt.base_cost if wt else 0.0

            if self.work_id:
                work = self.db.query(Work).get(self.work_id)
                work.title = title
                work.description = desc
                work.work_type_id = work_type_id
                work.responsible_id = resp_id
                work.status = status
                work.end_date = end_date

                self.db.query(WorkTeam).filter(WorkTeam.work_id == work.id).delete()
            else:
                work = Work(
                    title=title, description=desc, work_type_id=work_type_id,
                    author_id=self.current_user_id, responsible_id=resp_id,
                    status=status, end_date=end_date
                )
                self.db.add(work)
                self.db.commit()

            main_team = WorkTeam(work_id=work.id, employee_id=resp_id, amount_to_pay=base_cost, task_status='Назначен')
            self.db.add(main_team)

            for t_id in self.team_member_ids:
                extra_team = WorkTeam(work_id=work.id, employee_id=t_id, amount_to_pay=base_cost,
                                      task_status='Назначен')
                self.db.add(extra_team)

            self.db.commit()
            self.accept()

        except Exception as e:
            self.db.rollback()
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось сохранить работу:\n{e}")

    def delete_work(self):
        if self.work_id:
            try:
                work = self.db.query(Work).get(self.work_id)
                self.db.delete(work)
                self.db.commit()
            except Exception as e:
                self.db.rollback()
        self.accept()

    def closeEvent(self, event):
        self.db.close()


class HeadWorkspace(QWidget):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.db = SessionLocal()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.tab_control = QWidget()
        self.setup_control_tab()
        self.tabs.addTab(self.tab_control, "Создание и контроль работы")

        self.tab_review = QWidget()
        self.setup_review_tab()
        self.tabs.addTab(self.tab_review, "Выполненные работы")

    def setup_control_tab(self):
        layout = QVBoxLayout(self.tab_control)

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

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.works_container = QWidget()
        self.works_layout = QVBoxLayout(self.works_container)
        self.works_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.works_container)

        layout.addWidget(self.scroll_area)
        self.load_works()

    def setup_review_tab(self):
        layout = QVBoxLayout(self.tab_review)

        btn_refresh = QPushButton("Обновить список на проверку")
        btn_refresh.clicked.connect(self.load_review_works)
        layout.addWidget(btn_refresh, alignment=Qt.AlignRight)

        self.review_scroll = QScrollArea()
        self.review_scroll.setWidgetResizable(True)
        self.review_container = QWidget()
        self.review_layout = QVBoxLayout(self.review_container)
        self.review_layout.setAlignment(Qt.AlignTop)
        self.review_scroll.setWidget(self.review_container)
        layout.addWidget(self.review_scroll)

        self.load_review_works()

    def load_review_works(self):
        for i in reversed(range(self.review_layout.count())):
            widget = self.review_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)

        works_to_review = self.db.query(Work).filter(Work.status == 'На проверке').all()
        for work in works_to_review:
            card = WorkCard(work, self.open_review_dialog)
            self.review_layout.addWidget(card)

    def open_review_dialog(self, work_id):
        dialog = ReviewDialog(work_id, self.db)
        if dialog.exec():
            self.load_works()
            self.load_review_works()

    def load_works(self):
        for i in reversed(range(self.works_layout.count())):
            widget = self.works_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)

        works = self.db.query(Work).all()
        for work in works:
            card = WorkCard(work, self.open_work_dialog)
            self.works_layout.addWidget(card)

    def open_work_dialog(self, work_id=None):
        dialog = WorkDialog(work_id, self.current_user.id)
        if dialog.exec():
            self.load_works()
