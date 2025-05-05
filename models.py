from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Table,
    Boolean, Text, Enum, MetaData, Float
)
from sqlalchemy.orm import relationship
import enum

metadata_obj = MetaData()

class TaskStatus(enum.Enum):
    todo = "todo"
    in_progress = "in_progress"
    review = "review"
    done = "done"
    blocked = "blocked"
    cancelled = "cancelled"

# Users table
users = Table(
    'users',
    metadata_obj,
    Column('id', Integer, primary_key=True),
    Column('username', String(50), unique=True, nullable=False),
    Column('email', String(120), unique=True, nullable=False),
    Column('full_name', String(100)),
    Column('password_hash', String(256), nullable=False),
    Column('salt', String(64), nullable=False),
    Column('created_at', DateTime, default=datetime.utcnow),
)

# Tasks table
tasks = Table(
    'tasks',
    metadata_obj,
    Column('id', Integer, primary_key=True),
    Column('title', String(200), nullable=False),
    Column('description', Text),
    Column('creator_id', Integer, ForeignKey('users.id'), nullable=False),
    Column('created_at', DateTime, default=datetime.utcnow),
    Column('status', Enum(TaskStatus), default=TaskStatus.todo),
    Column('soft_deadline', DateTime),
    Column('hard_deadline', DateTime),
    Column('completed_at', DateTime),
)

# Dashboard table - central aggregation table
dashboard = Table(
    'dashboard',
    metadata_obj,
    Column('id', Integer, primary_key=True),
    Column('task_id', Integer, ForeignKey('tasks.id'), unique=True, nullable=False),
    Column('title', String(200), nullable=False),
    Column('description', Text),
    Column('assignee_id', Integer, ForeignKey('users.id')),
    Column('assignee_name', String(100)),
    Column('created_at', DateTime, nullable=False),
    Column('status', Enum(TaskStatus), nullable=False),
    Column('soft_deadline', DateTime),
    Column('hard_deadline', DateTime)
)

# Task dependencies (parent-child relationships)
task_dependencies = Table(
    'task_dependencies',
    metadata_obj,
    Column('id', Integer, primary_key=True),
    Column('parent_task_id', Integer, ForeignKey('tasks.id'), nullable=False),
    Column('child_task_id', Integer, ForeignKey('tasks.id'), nullable=False),
    Column('created_at', DateTime, default=datetime.utcnow),
)

# Parallel tasks
task_parallel = Table(
    'task_parallel',
    metadata_obj,
    Column('id', Integer, primary_key=True),
    Column('task_id_1', Integer, ForeignKey('tasks.id'), nullable=False),
    Column('task_id_2', Integer, ForeignKey('tasks.id'), nullable=False),
    Column('created_at', DateTime, default=datetime.utcnow),
)

# Task assignees (many-to-many)
task_assignees = Table(
    'task_assignees',
    metadata_obj,
    Column('id', Integer, primary_key=True),
    Column('task_id', Integer, ForeignKey('tasks.id'), nullable=False),
    Column('user_id', Integer, ForeignKey('users.id'), nullable=False),
    Column('assigned_at', DateTime, default=datetime.utcnow),
    Column('is_primary', Boolean, default=False),
)

# Custom fields definitions
task_custom_fields = Table(
    'task_custom_fields',
    metadata_obj,
    Column('id', Integer, primary_key=True),
    Column('name', String(50), nullable=False),
    Column('field_type', String(20), nullable=False),  # text, number, date, etc.
    Column('created_at', DateTime, default=datetime.utcnow),
)

# Custom field values
task_custom_values = Table(
    'task_custom_values',
    metadata_obj,
    Column('id', Integer, primary_key=True),
    Column('task_id', Integer, ForeignKey('tasks.id'), nullable=False),
    Column('field_id', Integer, ForeignKey('task_custom_fields.id'), nullable=False),
    Column('value', Text),
    Column('created_at', DateTime, default=datetime.utcnow),
)

# Task comments
task_comments = Table(
    'task_comments',
    metadata_obj,
    Column('id', Integer, primary_key=True),
    Column('task_id', Integer, ForeignKey('tasks.id'), nullable=False),
    Column('user_id', Integer, ForeignKey('users.id'), nullable=False),
    Column('content', Text, nullable=False),
    Column('created_at', DateTime, default=datetime.utcnow),
)

# Task history
task_history = Table(
    'task_history',
    metadata_obj,
    Column('id', Integer, primary_key=True),
    Column('task_id', Integer, ForeignKey('tasks.id'), nullable=False),
    Column('user_id', Integer, ForeignKey('users.id'), nullable=False),
    Column('field_changed', String(50), nullable=False),
    Column('old_value', Text),
    Column('new_value', Text),
    Column('changed_at', DateTime, default=datetime.utcnow),
)

# Task permissions
task_permissions = Table(
    'task_permissions',
    metadata_obj,
    Column('id', Integer, primary_key=True),
    Column('task_id', Integer, nullable=False),
    Column('user_id', Integer, ForeignKey('users.id'), nullable=False),
    Column('permission_level', String(20), nullable=False),  # 'owner', 'edit', 'read', 'none'
    Column('created_at', DateTime, default=datetime.utcnow),
) 
