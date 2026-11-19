from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from .config import settings

# Handle sqlite specific connect args for multi-threaded FastAPI
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """FastAPI database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def seed_demo_project_if_empty(db: Session) -> None:
    """Pre-seed the Swag Labs E-Commerce demo suite if no projects exist."""
    from .models.project import Project, IngestionType
    from pathlib import Path
    import zipfile

    if db.query(Project).count() == 0:
        demo_dir = Path(__file__).resolve().parent.parent.parent / "demo"
        suite_dir = demo_dir / "ecommerce-playwright-suite"
        zip_path = demo_dir / "ecommerce-playwright-suite.zip"

        if suite_dir.exists() and not zip_path.exists():
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for file in suite_dir.rglob("*"):
                    if file.is_file():
                        zf.write(file, file.relative_to(suite_dir))

        demo_proj = Project(
            id="demo-ecommerce-suite",
            name="Swag Labs E-Commerce Regression",
            description="Playwright E2E suite covering login, catalog sorting, 3-step checkout, and failure screenshot capture.",
            ingestion_type=IngestionType.ZIP,
            zip_storage_path=str(zip_path),
        )
        db.add(demo_proj)
        db.commit()

def init_db() -> None:
    """Create all registered tables and seed demo project."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_demo_project_if_empty(db)
    finally:
        db.close()
