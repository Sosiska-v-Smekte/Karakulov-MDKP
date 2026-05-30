from sqlalchemy import Column, Integer, String, Boolean, Numeric, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import date
from .database import Base


class Employee(Base):
    """Таблица 1: Информация о сотрудниках (Базовая таблица)"""
    __tablename__ = 'employees'

    id = Column(Integer, primary_key=True, autoincrement=True)
    last_name = Column(String(50), nullable=False)
    first_name = Column(String(50), nullable=False)
    middle_name = Column(String(50))

    # Тип сотрудника: 'head', 'teacher', 'accountant', 'uvp'
    role = Column(String(20), nullable=False)

    login = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    # Контактные данные и аватар (из наших дополнений к логике профиля)
    email = Column(String(100), unique=True)
    phone = Column(String(20))
    avatar_path = Column(String(255), default="default_avatar.png")

    base_rate = Column(Numeric(10, 2), default=0.00)
    is_active = Column(Boolean, default=True)

    # Связи с дочерними таблицами (One-to-One)
    teacher_info = relationship("Teacher", back_populates="employee", uselist=False, cascade="all, delete-orphan")
    uvp_info = relationship("SupportStaff", back_populates="employee", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<{self.last_name} {self.first_name[0]}. (Role: {self.role})>"


class Teacher(Base):
    """Таблица 2: Дополнительная информация о преподавателях"""
    __tablename__ = 'teachers'

    employee_id = Column(Integer, ForeignKey('employees.id'), primary_key=True)
    academic_degree = Column(String(100))  # Ученая степень
    academic_rank = Column(String(100))  # Ученое звание

    employee = relationship("Employee", back_populates="teacher_info")


class SupportStaff(Base):
    """Таблица 3: Дополнительные сведения об УВП"""
    __tablename__ = 'support_staff'

    employee_id = Column(Integer, ForeignKey('employees.id'), primary_key=True)
    position = Column(String(100))  # Должность

    employee = relationship("Employee", back_populates="uvp_info")


class WorkType(Base):
    """Таблица 4: Классификатор работ"""
    __tablename__ = 'work_types'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    base_cost = Column(Numeric(10, 2), nullable=False)
    unit = Column(String(20))  # Единица измерения (часы, штуки и т.д.)
    is_active = Column(Boolean, default=True)

    works = relationship("Work", back_populates="work_type")


class Work(Base):
    """Таблица 5: Дополнительные работы (Задачи)"""
    __tablename__ = 'works'

    id = Column(Integer, primary_key=True, autoincrement=True)
    work_type_id = Column(Integer, ForeignKey('work_types.id'), nullable=False)
    author_id = Column(Integer, ForeignKey('employees.id'), nullable=False)  # Заведующий
    responsible_id = Column(Integer, ForeignKey('employees.id'), nullable=False)  # Главный ответственный

    title = Column(String(200), nullable=False)
    description = Column(Text)  # Подробное описание из наших дополнений
    workload = Column(Integer)  # Трудоемкость
    is_urgent = Column(Boolean, default=False)

    start_date = Column(Date, default=date.today)
    end_date = Column(Date)

    # Статусы: 'Запланирована', 'В работе', 'На проверке', 'Завершена', 'Отменена'
    status = Column(String(20), default='Запланирована')

    # Связи
    work_type = relationship("WorkType", back_populates="works")
    author = relationship("Employee", foreign_keys=[author_id])
    responsible = relationship("Employee", foreign_keys=[responsible_id])
    team_members = relationship("WorkTeam", back_populates="work", cascade="all, delete-orphan")


class WorkTeam(Base):
    """Таблица 6: Состав исполнителей (Для трудоемких работ и отчетов)"""
    __tablename__ = 'work_teams'

    id = Column(Integer, primary_key=True, autoincrement=True)
    work_id = Column(Integer, ForeignKey('works.id'), nullable=False)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False)

    hours_worked = Column(Integer, default=0)
    amount_to_pay = Column(Numeric(10, 2), default=0.00)

    # Статусы выполнения конкретным участником: 'Назначен', 'В работе', 'Выполнено'
    task_status = Column(String(20), default='Назначен')

    # Путь к прикрепленному файлу-отчету от преподавателя/УВП
    report_file_path = Column(String(255))

    # Связи
    work = relationship("Work", back_populates="team_members")
    employee = relationship("Employee")
    payment = relationship("Payment", back_populates="work_team", uselist=False)


class Payment(Base):
    """Таблица 7: Выплаты"""
    __tablename__ = 'payments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    work_team_id = Column(Integer, ForeignKey('work_teams.id'), unique=True, nullable=False)

    payment_date = Column(Date)
    amount = Column(Numeric(10, 2), nullable=False)

    # Путь к файлу-квитанции, который прикрепляет бухгалтер
    receipt_file_path = Column(String(255))

    # Статус оплаты: 'Ожидает', 'Выплачено'
    payment_status = Column(String(20), default='Ожидает')

    # Связи
    work_team = relationship("WorkTeam", back_populates="payment")