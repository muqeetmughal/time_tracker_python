import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, DateTime, Integer, Float, Text,
    Index, ForeignKey, LargeBinary
)
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


def utc_now():
    return datetime.now(timezone.utc)


class Activity(Base):
    __tablename__ = "activities"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, nullable=False, index=True)

    project_id = Column(String, nullable=True, index=True)
    task_id = Column(String, nullable=True, index=True)
    activity_type = Column(String, nullable=True)

    description = Column(Text, nullable=False)
    expected_hours = Column(Float, nullable=True)

    start_time = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    screenshots_count = Column(Integer, nullable=False, default=0)
    camshots_count = Column(Integer, nullable=False, default=0)
    keyboard_count = Column(Integer, nullable=False, default=0)
    mouse_click_count = Column(Integer, nullable=False, default=0)

    status = Column(String, nullable=False, default="active")
    sync_status = Column(String, nullable=False, default="pending")

    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    media_items = relationship("ActivityMedia", back_populates="activity", cascade="all, delete-orphan")
    input_intervals = relationship("ActivityInput", back_populates="activity", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_activities_session_status", "session_id", "status"),
        Index("idx_activities_session_start_time", "session_id", "start_time"),
        Index("idx_activities_sync_status", "sync_status"),
    )

    def close(self):
        self.end_time = utc_now()
        self.status = "completed"
        start_time = self.start_time
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        self.duration_seconds = int((self.end_time - start_time).total_seconds())


class ActivityMedia(Base):
    __tablename__ = "activity_media"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    activity_id = Column(String, ForeignKey("activities.id"), nullable=False, index=True)
    media_type = Column(String, nullable=False, default="screenshot")
    filename = Column(String, nullable=True)
    file_data = Column(LargeBinary, nullable=True)
    file_size = Column(Integer, nullable=True)
    file_path = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending")
    sync_status = Column(String, nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    activity = relationship("Activity", back_populates="media_items")

    __table_args__ = (
        Index("idx_media_activity", "activity_id"),
        Index("idx_media_status", "status"),
        Index("idx_media_sync_status", "sync_status"),
    )


class ActivityInput(Base):
    __tablename__ = "activity_inputs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    activity_id = Column(String, ForeignKey("activities.id"), nullable=False, index=True)
    keyboard_count = Column(Integer, nullable=False, default=0)
    mouse_click_count = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    activity = relationship("Activity", back_populates="input_intervals")

    __table_args__ = (
        Index("idx_input_activity", "activity_id"),
    )
