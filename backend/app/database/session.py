"""
数据库 Session 管理
"""
from app.database.base import SessionLocal
from typing import Generator


def get_db() -> Generator:
    """
    获取数据库 Session
    
    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
