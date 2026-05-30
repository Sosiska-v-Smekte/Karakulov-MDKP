import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QIcon
from core.models import Employee
from core.database import SessionLocal
from gui.profile_window import ProfileDialog

class BaseWindow(QMainWindow):
    def __init__(self, current_user: Employee):
        super().__init__()
        self.current_user = current_user
        self.setWindowTitle("Информационная система кафедры — ИКИТ (КИ24-06Б)")
        self.setMinimumSize(1024, 768)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.setup_header()
        self.setup_workspace()

    def setup_header(self):
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #2c3e50; color: white;")
        header_frame.setFixedHeight(60)
        header_layout = QHBoxLayout(header_frame)

        logo_label = QLabel("Управление дополнительными работами — КИ24-06Б")
        logo_label.setStyleSheet("font-size: 16px; font-weight: bold; padding-left: 15px;")
        header_layout.addWidget(logo_label)

        header_layout.addStretch()

        user_info_label = QLabel(
            f"{self.current_user.last_name} {self.current_user.first_name[0]}.{self.current_user.middle_name[0] if self.current_user.middle_name else ''}.\n"
            f"Статус: {self.get_role_name()}"
        )
        user_info_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header_layout.addWidget(user_info_label)

        self.avatar_clickable = QPushButton()
        self.avatar_clickable.setFixedSize(40, 40)
        self.avatar_clickable.setCursor(Qt.PointingHandCursor)

        if self.current_user.avatar_path and os.path.exists(self.current_user.avatar_path):
            pixmap = QPixmap(self.current_user.avatar_path)
        else:
            pixmap = QPixmap(40, 40)
            pixmap.fill(Qt.lightGray)

        self.avatar_clickable.setStyleSheet("border-radius: 20px; border: 1px solid white;")
        self.avatar_clickable.setIcon(QIcon(pixmap.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
        self.avatar_clickable.setIconSize(self.avatar_clickable.size())

        self.avatar_clickable.clicked.connect(self.open_profile_settings)
        header_layout.addWidget(self.avatar_clickable)

        self.main_layout.addWidget(header_frame)

    def setup_workspace(self):
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
        dialog = ProfileDialog(self.current_user.id, self)
        dialog.logout_requested.connect(self.trigger_system_logout)

        if dialog.exec():
            db = SessionLocal()
            fresh_user = db.query(Employee).get(self.current_user.id)
            if fresh_user.avatar_path and os.path.exists(fresh_user.avatar_path):
                pixmap = QPixmap(fresh_user.avatar_path)
                self.avatar_clickable.setIcon(QIcon(pixmap.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
            db.close()

    def trigger_system_logout(self):
        self.close()
        from PySide6.QtWidgets import QApplication
        for widget in QApplication.topLevelWidgets():
            if widget != self:
                widget.close()