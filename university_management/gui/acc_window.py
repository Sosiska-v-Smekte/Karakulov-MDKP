import os
import shutil
from datetime import date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QScrollArea, QTabWidget, QDialog, QFileDialog, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, QDoubleSpinBox
)
from PySide6.QtCore import Qt
from core.database import SessionLocal
from core.models import Work, WorkTeam, Payment, WorkType
from utils.export import export_payments_to_excel
from utils.export import import_work_types_from_excel


class WorkTypeDialog(QDialog):
    """Полноценное окно создания нового типа работы"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Добавление типа работы")
        self.setFixedSize(350, 150)

        layout = QFormLayout(self)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Например: Проверка контрольных")

        self.cost_input = QDoubleSpinBox()
        self.cost_input.setMaximum(1000000.00)  # Максимальная сумма
        self.cost_input.setSuffix(" руб.")

        layout.addRow("Название работы:", self.name_input)
        layout.addRow("Базовая ставка:", self.cost_input)

        btn_save = QPushButton("Добавить в справочник")
        btn_save.setStyleSheet("background-color: #4CAF50; color: white;")
        btn_save.clicked.connect(self.accept)
        layout.addRow(btn_save)

    def get_data(self):
        return self.name_input.text().strip(), self.cost_input.value()

class PaymentCard(QFrame):
    """Карточка выплаты для очередей и истории"""

    def __init__(self, team_record, is_history, click_callback):
        super().__init__()
        self.team_record_id = team_record.id
        self.is_history = is_history
        self.click_callback = click_callback

        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(80)

        layout = QHBoxLayout(self)

        info_layout = QVBoxLayout()
        # Показываем ФИО сотрудника и название работы
        emp = team_record.employee
        emp_name = f"{emp.last_name} {emp.first_name} {emp.middle_name or ''}"

        title = QLabel(f"<b>{emp_name}</b> (ID: {emp.id})")
        work_title = QLabel(f"Работа: {team_record.work.title}")
        info_layout.addWidget(title)
        info_layout.addWidget(work_title)
        layout.addLayout(info_layout)

        # Сумма и статус
        amount_label = QLabel(f"<b>{team_record.amount_to_pay} руб.</b>")
        amount_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        if self.is_history:
            self.setStyleSheet("background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 5px;")  # Зеленый
        else:
            self.setStyleSheet("background-color: #fff3cd; border: 1px solid #ffeeba; border-radius: 5px;")  # Желтый

        layout.addWidget(amount_label)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.click_callback(self.team_record_id, self.is_history)


class PaymentProcessDialog(QDialog):
    """Окно подтверждения выплаты и прикрепления квитанции"""

    def __init__(self, team_record_id, is_history=False):
        super().__init__()
        self.team_record_id = team_record_id
        self.is_history = is_history
        self.db = SessionLocal()
        self.selected_file_path = None

        title = "Просмотр выплаты" if is_history else "Начисление выплаты"
        self.setWindowTitle(title)
        self.setMinimumSize(450, 350)

        self.setup_ui()

    def setup_ui(self):
        self.team_record = self.db.query(WorkTeam).get(self.team_record_id)
        work = self.team_record.work
        emp = self.team_record.employee

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(f"<h3>Сотрудник: {emp.last_name} {emp.first_name} (ID: {emp.id})</h3>"))
        layout.addWidget(QLabel(f"<b>Работа:</b> {work.title}"))
        layout.addWidget(QLabel(f"<b>Дата завершения:</b> {work.end_date}"))

        # Заглушка для банковских реквизитов (их можно добавить в Employee позже)
        layout.addWidget(QLabel("<b>Банковские данные:</b> Сбербанк, р/с 40817810..."))

        layout.addWidget(QLabel(f"<h3 style='color: #27ae60;'>К выплате: {self.team_record.amount_to_pay} руб.</h3>"))

        layout.addStretch()

        if self.is_history:
            payment = self.team_record.payment
            layout.addWidget(QLabel(f"<b>Дата выплаты:</b> {payment.payment_date}"))
            if payment.receipt_file_path:
                layout.addWidget(QLabel(f"<b>Квитанция:</b> Прикреплена (можно скачать)"))
        else:
            # Блок прикрепления чека
            file_layout = QHBoxLayout()
            self.file_label = QLabel("Квитанция не выбрана")
            btn_attach = QPushButton("Прикрепить квитанцию")
            btn_attach.clicked.connect(self.attach_file)

            file_layout.addWidget(self.file_label)
            file_layout.addWidget(btn_attach)
            layout.addLayout(file_layout)

            btn_submit = QPushButton("Подтвердить выплату")
            btn_submit.setStyleSheet("background-color: #4CAF50; color: white; height: 35px; font-weight: bold;")
            btn_submit.clicked.connect(self.confirm_payment)
            layout.addWidget(btn_submit)

    def attach_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите файл квитанции", "",
                                                   "All Files (*);;PDF (*.pdf);;Images (*.png *.jpg)")
        if file_path:
            self.selected_file_path = file_path
            self.file_label.setText(os.path.basename(file_path))

    def confirm_payment(self):
        dest_path = None
        if self.selected_file_path:
            upload_dir = "uploads/receipts"
            os.makedirs(upload_dir, exist_ok=True)
            filename = os.path.basename(self.selected_file_path)
            dest_path = os.path.join(upload_dir, f"receipt_{self.team_record.id}_{filename}")
            shutil.copy(self.selected_file_path, dest_path)

        # Создаем запись о выплате
        new_payment = Payment(
            work_team_id=self.team_record.id,
            payment_date=date.today(),
            amount=self.team_record.amount_to_pay,
            receipt_file_path=dest_path,
            payment_status='Выплачено'
        )
        self.db.add(new_payment)
        self.db.commit()
        self.accept()

    def closeEvent(self, event):
        self.db.close()


class AccountantWorkspace(QWidget):
    """Главный виджет рабочего пространства Бухгалтера"""

    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.db = SessionLocal()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Вкладки
        self.tab_pending = QWidget()
        self.tab_history = QWidget()
        self.tab_directories = QWidget()

        self.setup_pending_tab()
        self.setup_history_tab()
        self.setup_directories_tab()

        self.tabs.addTab(self.tab_pending, "Начисление выплат")
        self.tabs.addTab(self.tab_history, "История выплат")
        self.tabs.addTab(self.tab_directories, "Ведение справочников")

    def setup_pending_tab(self):
        layout = QVBoxLayout(self.tab_pending)
        btn_refresh = QPushButton("Обновить очередь")
        btn_refresh.clicked.connect(self.load_payments)
        layout.addWidget(btn_refresh, alignment=Qt.AlignRight)

        self.pending_scroll = QScrollArea()
        self.pending_scroll.setWidgetResizable(True)
        self.pending_container = QWidget()
        self.pending_layout = QVBoxLayout(self.pending_container)
        self.pending_layout.setAlignment(Qt.AlignTop)
        self.pending_scroll.setWidget(self.pending_container)
        layout.addWidget(self.pending_scroll)

    def setup_history_tab(self):
        layout = QVBoxLayout(self.tab_history)
        btn_refresh = QPushButton("Обновить архив")
        btn_refresh.clicked.connect(self.load_payments)
        layout.addWidget(btn_refresh, alignment=Qt.AlignRight)

        self.history_scroll = QScrollArea()
        self.history_scroll.setWidgetResizable(True)
        self.history_container = QWidget()
        self.history_layout = QVBoxLayout(self.history_container)
        self.history_layout.setAlignment(Qt.AlignTop)
        self.history_scroll.setWidget(self.history_container)
        layout.addWidget(self.history_scroll)

        self.load_payments()

        btn_export = QPushButton("Экспорт в Excel")
        btn_export.setStyleSheet("background-color: #27ae60; color: white;")
        btn_export.clicked.connect(self.export_history)
        layout.addWidget(btn_export, alignment=Qt.AlignRight)

    def setup_directories_tab(self):
        """Интерфейс для работы со справочником (CRUD для типов работ)"""
        layout = QVBoxLayout(self.tab_directories)

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("<b>Справочник: Классификатор работ и ставки</b>"))
        toolbar.addStretch()

        btn_add = QPushButton("+ Добавить тип работы")
        btn_add.clicked.connect(self.add_work_type)
        toolbar.addWidget(btn_add)

        btn_refresh = QPushButton("Обновить")
        btn_refresh.clicked.connect(self.load_directories)
        toolbar.addWidget(btn_refresh)

        layout.addLayout(toolbar)

        self.dir_table = QTableWidget()
        self.dir_table.setColumnCount(3)
        self.dir_table.setHorizontalHeaderLabels(["ID", "Название", "Базовая ставка (руб)"])
        self.dir_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.dir_table)

        self.load_directories()

        btn_import = QPushButton("Импорт из Excel")
        btn_import.clicked.connect(self.import_directories)
        toolbar.addWidget(btn_import)

    def load_payments(self):
        """Загрузка очередей на оплату и архива"""
        for i in reversed(range(self.pending_layout.count())):
            self.pending_layout.itemAt(i).widget().setParent(None)
        for i in reversed(range(self.history_layout.count())):
            self.history_layout.itemAt(i).widget().setParent(None)

        # Выбираем всех участников, у которых основная работа "Завершена"
        completed_tasks = self.db.query(WorkTeam).join(Work).filter(
            Work.status == 'Завершена'
        ).all()

        for task in completed_tasks:
            # Проверяем, есть ли уже запись об оплате для этого участника
            payment = self.db.query(Payment).filter(Payment.work_team_id == task.id).first()

            if payment and payment.payment_status == 'Выплачено':
                card = PaymentCard(task, is_history=True, click_callback=self.open_payment_dialog)
                self.history_layout.addWidget(card)
            else:
                card = PaymentCard(task, is_history=False, click_callback=self.open_payment_dialog)
                self.pending_layout.addWidget(card)

    def open_payment_dialog(self, team_record_id, is_history):
        dialog = PaymentProcessDialog(team_record_id, is_history)
        if dialog.exec():
            self.load_payments()

    def load_directories(self):
        """Загружает данные в таблицу справочников"""
        work_types = self.db.query(WorkType).all()
        self.dir_table.setRowCount(len(work_types))

        for row, wt in enumerate(work_types):
            self.dir_table.setItem(row, 0, QTableWidgetItem(str(wt.id)))
            self.dir_table.setItem(row, 1, QTableWidgetItem(wt.name))
            self.dir_table.setItem(row, 2, QTableWidgetItem(str(wt.base_cost)))

    def add_work_type(self):
        """Рабочий метод добавления в базу данных"""
        dialog = WorkTypeDialog()
        if dialog.exec():
            name, cost = dialog.get_data()
            if not name:
                QMessageBox.warning(self, "Ошибка", "Название работы не может быть пустым!")
                return

            try:
                new_type = WorkType(name=name, base_cost=cost, unit="шт/час", is_active=True)
                self.db.add(new_type)
                self.db.commit()
                self.load_directories()  # Сразу обновляем таблицу на экране
                QMessageBox.information(self, "Успех", f"Работа «{name}» добавлена!")
            except Exception as e:
                self.db.rollback()
                QMessageBox.critical(self, "Ошибка БД", str(e))

    def export_history(self):
        filepath, _ = QFileDialog.getSaveFileName(self, "Сохранить отчет", "Отчет_по_выплатам.xlsx",
                                                  "Excel Files (*.xlsx)")
        if filepath:
            success, message = export_payments_to_excel(self.db, filepath)
            if success:
                QMessageBox.information(self, "Успех", message)
            else:
                QMessageBox.critical(self, "Ошибка", f"Не удалось экспортировать: {message}")

    def import_directories(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Выберите файл справочника", "", "Excel Files (*.xlsx)")
        if filepath:
            success, message = import_work_types_from_excel(self.db, filepath)
            if success:
                QMessageBox.information(self, "Успех", message)
                self.load_directories()  # Обновляем таблицу на экране
            else:
                QMessageBox.critical(self, "Ошибка", f"Не удалось импортировать: {message}")