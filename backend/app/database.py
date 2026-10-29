from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from .config import settings

class Base(DeclarativeBase): pass

class AnalysisSessionRecord(Base):
    __tablename__ = "analysis_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    question: Mapped[str] = mapped_column(String(500), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)

class UserRecord(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True, nullable=False)
    phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class OtpChallengeRecord(Base):
    __tablename__ = "otp_challenges"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

class ProjectRecord(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("analysis_sessions.id"), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

engine = create_engine(settings.database_url, future=True)

def initialise_database() -> None: Base.metadata.create_all(engine)

def save_session(session_data) -> None:
    with Session(engine) as db:
        db.merge(AnalysisSessionRecord(id=session_data.id, created_at=session_data.created_at, question=session_data.question, payload=session_data.model_dump(mode="json")))
        db.commit()

def load_session(session_id: str) -> dict | None:
    with Session(engine) as db:
        record = db.get(AnalysisSessionRecord, session_id)
        return record.payload if record else None

def save_project(user_id: str, session_id: str, title: str, created_at: datetime) -> None:
    from uuid import uuid4
    with Session(engine) as db:
        db.add(ProjectRecord(id=str(uuid4()), user_id=user_id, session_id=session_id, title=title, created_at=created_at))
        db.commit()

def projects_for_user(user_id: str) -> list[ProjectRecord]:
    with Session(engine) as db:
        return list(db.query(ProjectRecord).filter(ProjectRecord.user_id == user_id).order_by(ProjectRecord.created_at.desc()).all())

def session_belongs_to_user(user_id: str, session_id: str) -> bool:
    with Session(engine) as db:
        return db.query(ProjectRecord).filter(ProjectRecord.user_id == user_id, ProjectRecord.session_id == session_id).first() is not None
