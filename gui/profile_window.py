import os
import shutil
import bcrypt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFileDialog, QMessageBox, QFormLayout, QComboBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from core.database import SessionLocal
from core.models import Employee


class ProfileDialog(QDialog):
    logout_requested = Signal()

    def __init__(self, user_id, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.db = SessionLocal()
        self.selected_avatar_path = None

        self.user = self.db.query(Employee).get(self.user_id)

        self.setWindowTitle("Личный профиль сотрудника")
        self.setFixedSize(450, 650)

        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)

        avatar_layout = QVBoxLayout()
        avatar_layout.setAlignment(Qt.AlignCenter)

        self.avatar_img_label = QLabel()
        self.avatar_img_label.setFixedSize(120, 120)
        self.avatar_img_label.setAlignment(Qt.AlignCenter)
        self.update_avatar_preview(self.user.avatar_path)
        avatar_layout.addWidget(self.avatar_img_label)

        btn_change_photo = QPushButton("Изменить фотографию")
        btn_change_photo.setCursor(Qt.PointingHandCursor)
        btn_change_photo.setStyleSheet("background-color: #34495e; color: white; padding: 5px;")
        btn_change_photo.clicked.connect(self.choose_avatar_file)
        avatar_layout.addWidget(btn_change_photo)

        main_layout.addLayout(avatar_layout)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.id_input = QLineEdit(str(self.user.id))
        self.id_input.setReadOnly(True)
        self.id_input.setStyleSheet("background-color: #f0f0f0; color: #7f8c8d;")

        self.role_combo = QComboBox()
        self.role_combo.addItem("Заведующий кафедрой", "head")
        self.role_combo.addItem("Преподаватель", "teacher")
        self.role_combo.addItem("Бухгалтер", "accountant")
        self.role_combo.addItem("УВП", "uvp")
        index = self.role_combo.findData(self.user.role)
        if index >= 0:
            self.role_combo.setCurrentIndex(index)

        self.login_input = QLineEdit(self.user.login)
        self.email_input = QLineEdit(self.user.email or "")
        self.phone_input = QLineEdit(self.user.phone or "")

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Оставьте пустым, если не меняете")

        form_layout.addRow("ID аккаунта:", self.id_input)
        form_layout.addRow("Роль в системе:", self.role_combo)
        form_layout.addRow("Логин:", self.login_input)
        form_layout.addRow("Новый пароль:", self.password_input)
        form_layout.addRow("Email:", self.email_input)
        form_layout.addRow("Телефон:", self.phone_input)

        main_layout.addLayout(form_layout)
        main_layout.addStretch()

        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(10)

        btn_save = QPushButton("Сохранить изменения")
        btn_save.setFixedHeight(35)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        btn_save.clicked.connect(self.save_profile_data)
        btn_layout.addWidget(btn_save)

        btn_logout = QPushButton("Выйти из аккаунта")
        btn_logout.setFixedHeight(35)
        btn_logout.setCursor(Qt.PointingHandCursor)
        btn_logout.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold;")
        btn_logout.clicked.connect(self.handle_logout_click)
        btn_layout.addWidget(btn_logout)

        main_layout.addLayout(btn_layout)

    def update_avatar_preview(self, path):
        if path and os.path.exists(path):
            pixmap = QPixmap(path)
        else:
            pixmap = QPixmap(120, 120)
            pixmap.fill(Qt.lightGray)
        self.avatar_img_label.setPixmap(pixmap.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def choose_avatar_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите фотографию", "", "Изображения (*.png *.jpg *.jpeg)"
        )
        if file_path:
            self.selected_avatar_path = file_path
            self.update_avatar_preview(file_path)

    def save_profile_data(self):
        login = self.login_input.text().strip()
        email = self.email_input.text().strip()
        phone = self.phone_input.text().strip()
        password = self.password_input.text().strip()
        new_role = self.role_combo.currentData()

        if not login:
            QMessageBox.warning(self, "Ошибка", "Логин не может быть пустым!")
            return

        try:
            old_role = self.user.role

            if self.selected_avatar_path:
                upload_dir = "uploads/avatars"
                os.makedirs(upload_dir, exist_ok=True)
                ext = os.path.splitext(self.selected_avatar_path)[1]
                dest_filename = f"user_{self.user.id}{ext}"
                dest_path = os.path.join(upload_dir, dest_filename)
                shutil.copy(self.selected_avatar_path, dest_path)
                self.user.avatar_path = dest_path

            self.user.role = new_role
            self.user.login = login
            self.user.email = email
            self.user.phone = phone

            if password:
                salt = bcrypt.gensalt()
                self.user.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

            self.db.commit()

            if old_role != new_role:
                QMessageBox.information(self, "Роль изменена",
                                        "Ваша роль была изменена. Пожалуйста, войдите в систему заново.")
                self.db.close()
                self.logout_requested.emit()
                self.reject()
            else:
                QMessageBox.information(self, "Успех", "Данные профиля успешно обновлены!")
                self.accept()

        except Exception as e:
            self.db.rollback()
            QMessageBox.critical(self, "Ошибка", f"Не удалось обновить профиль.\n{e}")

    def handle_logout_click(self):
        confirm = QMessageBox.question(
            self, "Выход", "Вы уверены, что хотите выйти?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.db.close()
            self.logout_requested.emit()
            self.reject()

    def closeEvent(self, event):
        self.db.close()