from app.application import application
from app.services.automation import Automation
from app.services.events import EventBus
from app.services.project import ProjectService

bus = EventBus()
automation = Automation(application)
automation.attach(bus)
project_service = ProjectService(application.context.settings, bus)
