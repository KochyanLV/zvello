from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, Enum, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()

class TaskStatus(enum.Enum):
    todo = "todo"
    in_progress = "in_progress"
    review = "review"
    done = "done"
    blocked = "blocked"
    cancelled = "cancelled"

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    full_name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    password_hash = Column(String(256), nullable=False)
    salt = Column(String(64), nullable=False)

    # Relationships
    created_tasks = relationship('Task', back_populates='creator', foreign_keys='Task.creator_id')
    assigned_tasks = relationship('TaskAssignee', back_populates='user')
    comments = relationship('TaskComment', back_populates='user')
    history_records = relationship('TaskHistory', back_populates='user')
    dashboard_items = relationship('Dashboard', back_populates='assignee')

class Task(Base):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    creator_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(Enum(TaskStatus), default=TaskStatus.todo)
    soft_deadline = Column(DateTime)
    hard_deadline = Column(DateTime)
    completed_at = Column(DateTime)

    # Relationships
    creator = relationship('User', back_populates='created_tasks', foreign_keys=[creator_id])
    assignees = relationship('TaskAssignee', back_populates='task')
    custom_values = relationship('TaskCustomValue', back_populates='task')
    comments = relationship('TaskComment', back_populates='task')
    history = relationship('TaskHistory', back_populates='task')
    
    # Task dependencies relationships
    parent_tasks = relationship('TaskDependency', foreign_keys='TaskDependency.child_task_id', back_populates='child_task')
    child_tasks = relationship('TaskDependency', foreign_keys='TaskDependency.parent_task_id', back_populates='parent_task')
    
    # Parallel tasks relationships
    parallel_tasks_1 = relationship('TaskParallel', foreign_keys='TaskParallel.task_id_1', back_populates='task1')
    parallel_tasks_2 = relationship('TaskParallel', foreign_keys='TaskParallel.task_id_2', back_populates='task2')
    
    # Dashboard relationship
    dashboard = relationship('Dashboard', back_populates='task', uselist=False)

class Dashboard(Base):
    __tablename__ = 'dashboard'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), unique=True, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    assignee_id = Column(Integer, ForeignKey('users.id'))
    assignee_name = Column(String(100))
    created_at = Column(DateTime, nullable=False)
    status = Column(Enum(TaskStatus), nullable=False)
    soft_deadline = Column(DateTime)
    hard_deadline = Column(DateTime)
    parent_task_id = Column(Integer, nullable=True)
    
    # Relationships
    task = relationship('Task', back_populates='dashboard')
    assignee = relationship('User', back_populates='dashboard_items')
    parent_tasks = relationship('TaskDependency', secondary='task_dependencies', 
                              primaryjoin='Dashboard.task_id==TaskDependency.child_task_id',
                              secondaryjoin='TaskDependency.parent_task_id==Task.id',
                              viewonly=True)
    child_tasks = relationship('TaskDependency', secondary='task_dependencies',
                             primaryjoin='Dashboard.task_id==TaskDependency.parent_task_id',
                             secondaryjoin='TaskDependency.child_task_id==Task.id',
                             viewonly=True)
    parallel_tasks = relationship('TaskParallel', secondary='task_parallel',
                                primaryjoin='or_(Dashboard.task_id==TaskParallel.task_id_1, Dashboard.task_id==TaskParallel.task_id_2)',
                                secondaryjoin='or_(TaskParallel.task_id_1==Task.id, TaskParallel.task_id_2==Task.id)',
                                viewonly=True)

class TaskDependency(Base):
    __tablename__ = 'task_dependencies'

    id = Column(Integer, primary_key=True)
    parent_task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    child_task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    parent_task = relationship('Task', foreign_keys=[parent_task_id], back_populates='child_tasks')
    child_task = relationship('Task', foreign_keys=[child_task_id], back_populates='parent_tasks')

class TaskParallel(Base):
    __tablename__ = 'task_parallel'

    id = Column(Integer, primary_key=True)
    task_id_1 = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    task_id_2 = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    task1 = relationship('Task', foreign_keys=[task_id_1], back_populates='parallel_tasks_1')
    task2 = relationship('Task', foreign_keys=[task_id_2], back_populates='parallel_tasks_2')

class TaskAssignee(Base):
    __tablename__ = 'task_assignees'

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    is_primary = Column(Boolean, default=False)

    # Relationships
    task = relationship('Task', back_populates='assignees')
    user = relationship('User', back_populates='assigned_tasks')

class TaskCustomField(Base):
    __tablename__ = 'task_custom_fields'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    field_type = Column(String(20), nullable=False)  # text, number, date, etc.
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    values = relationship('TaskCustomValue', back_populates='field')

class TaskCustomValue(Base):
    __tablename__ = 'task_custom_values'

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    field_id = Column(Integer, ForeignKey('task_custom_fields.id'), nullable=False)
    value = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    task = relationship('Task', back_populates='custom_values')
    field = relationship('TaskCustomField', back_populates='values')

class TaskComment(Base):
    __tablename__ = 'task_comments'

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    task = relationship('Task', back_populates='comments')
    user = relationship('User', back_populates='comments')

class TaskHistory(Base):
    __tablename__ = 'task_history'

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    field_changed = Column(String(50), nullable=False)
    old_value = Column(Text)
    new_value = Column(Text)
    changed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    task = relationship('Task', back_populates='history')
    user = relationship('User', back_populates='history_records')

class TaskPermission(Base):
    __tablename__ = 'task_permissions'

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    permission_level = Column(String(20), nullable=False)  # 'owner', 'edit', 'read', 'none'
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    task = relationship('Task', back_populates='permissions')
    user = relationship('User', back_populates='permissions')

# Database connection and table creation
def init_db(database_url='sqlite:///tasks.db'):
    engine = create_engine(database_url)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return engine

if __name__ == '__main__':
    # Create tables when running this file directly
    engine = init_db()
    print("All tables have been created successfully!") 