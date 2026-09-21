from app.config import settings
from app.persistence.database import Database
from app.services.application import ApplicationContext, PlatformApplication

database = Database(settings.database_path)
database.initialize()

application = PlatformApplication(
    ApplicationContext(settings=settings, database=database)
)
