from app.config import Settings
from app.persistence.database import Database
from app.services.application import ApplicationContext, PlatformApplication

settings = Settings()
database = Database(settings.database_path)
database.initialize()

application = PlatformApplication(
    ApplicationContext(settings=settings, database=database)
)
