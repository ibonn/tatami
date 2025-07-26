import inspect
import os
from enum import Enum
from typing import Self

from pydantic import BaseModel, Field, computed_field

from tatami.config import find_config


class MessageLevel(Enum):
    DEFAULT = 'default'
    WARNING = 'warning'
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


class Message(BaseModel):
    level: MessageLevel
    message: str
    frame: inspect.FrameInfo = Field(default_factory=lambda: inspect.getframeinfo(inspect.currentframe()))

class Summary(BaseModel):
    warning: int = Field(default=0)
    low: int = Field(default=0)
    medium: int = Field(default=0)
    high: int = Field(default=0)
    critical: int = Field(default=0)
    

class Diagnose(BaseModel):
    detail: list[Message]

    @computed_field
    @property
    def summary(self) -> Summary:
        levels = {}
        for message in self.detail:
            if message.level == MessageLevel.DEFAULT:
                continue

            if message.level in levels:
                levels[message.level] += 1
            else:
                levels[message.level] = 1

        return Summary(**{level.value: count for level, count in levels.items()})

class Doctor:
    def __init__(self):
        self.diagnostics = []

    def add_message(self, msg: str, level: MessageLevel = MessageLevel.DEFAULT) -> Self:
        self.diagnostics.append(Message(
            level=level,
            message=msg,
        ))
        return self
    
    def get_diagnose(self) -> Diagnose:
        return Diagnose(detail=self.diagnostics)


def diagnose_project(project_path: str) -> Diagnose:
    """Diagnose a Tatami project and return a detailed analysis."""
    doctor = Doctor()
    
    # Check if project path exists
    if not os.path.exists(project_path):
        doctor.add_message(f"Project path '{project_path}' does not exist", MessageLevel.CRITICAL)
        return doctor.get_diagnose()
    
    if not os.path.isdir(project_path):
        doctor.add_message(f"Project path '{project_path}' is not a directory", MessageLevel.CRITICAL)
        return doctor.get_diagnose()
    
    doctor.add_message(f"Project path '{project_path}' found", MessageLevel.DEFAULT)
    
    # Check for configuration files
    config_path = find_config(project_path)
    if config_path:
        doctor.add_message(f"Configuration file found: {os.path.basename(config_path)}", MessageLevel.DEFAULT)
    else:
        doctor.add_message("No configuration file found (config.yaml or config.py)", MessageLevel.WARNING)
    
    # Check for routers directory
    routers_path = os.path.join(project_path, 'routers')
    if os.path.exists(routers_path) and os.path.isdir(routers_path):
        router_files = [f for f in os.listdir(routers_path) if f.endswith('.py') and f != '__init__.py']
        if router_files:
            doctor.add_message(f"Found {len(router_files)} router files: {', '.join(router_files)}", MessageLevel.DEFAULT)
        else:
            doctor.add_message("Routers directory exists but contains no Python files", MessageLevel.WARNING)
    else:
        doctor.add_message("No routers directory found", MessageLevel.MEDIUM)
    
    # Check for middleware directory
    middleware_path = os.path.join(project_path, 'middleware')
    if os.path.exists(middleware_path) and os.path.isdir(middleware_path):
        middleware_files = [f for f in os.listdir(middleware_path) if f.endswith('.py') and f != '__init__.py']
        if middleware_files:
            doctor.add_message(f"Found {len(middleware_files)} middleware files: {', '.join(middleware_files)}", MessageLevel.DEFAULT)
        else:
            doctor.add_message("Middleware directory exists but contains no Python files", MessageLevel.DEFAULT)
    else:
        doctor.add_message("No middleware directory found", MessageLevel.DEFAULT)
    
    # Check for static files
    static_path = os.path.join(project_path, 'static')
    if os.path.exists(static_path) and os.path.isdir(static_path):
        doctor.add_message("Static files directory found", MessageLevel.DEFAULT)
    else:
        doctor.add_message("No static directory found", MessageLevel.DEFAULT)
    
    # Check for templates
    templates_path = os.path.join(project_path, 'templates')
    if os.path.exists(templates_path) and os.path.isdir(templates_path):
        template_files = [f for f in os.listdir(templates_path) if f.endswith(('.html', '.jinja2', '.j2'))]
        if template_files:
            doctor.add_message(f"Found {len(template_files)} template files", MessageLevel.DEFAULT)
        else:
            doctor.add_message("Templates directory exists but contains no template files", MessageLevel.DEFAULT)
    else:
        doctor.add_message("No templates directory found", MessageLevel.DEFAULT)
    
    # Check for favicon
    favicon_path = os.path.join(project_path, 'favicon.ico')
    if os.path.exists(favicon_path):
        doctor.add_message("Custom favicon found", MessageLevel.DEFAULT)
    else:
        doctor.add_message("No custom favicon found (will use default)", MessageLevel.DEFAULT)
    
    # Check for README
    readme_path = os.path.join(project_path, 'README.md')
    if os.path.exists(readme_path):
        doctor.add_message("README.md found", MessageLevel.DEFAULT)
    else:
        doctor.add_message("No README.md found", MessageLevel.LOW)
    
    return doctor.get_diagnose()