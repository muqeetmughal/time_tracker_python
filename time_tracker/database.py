from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from time_tracker.models import Base
from time_tracker.utils.logger import logger


try:
    engine = create_engine("sqlite:///time_tracker.db", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    logger.debug("Database initialized: time_tracker.db")
except Exception as e:
    logger.critical("Database initialization failed: %s", e)
    raise
