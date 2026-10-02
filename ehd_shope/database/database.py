from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

try:
    from ehd_shope.config import DATABASE_URL
except ImportError:
    from config import DATABASE_URL

Base = declarative_base()
engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    try:
        from ehd_shope.database.models import (
            AdminUser,
            Cart,
            CartItem,
            Category,
            Order,
            OrderItem,
            Payment,
            Product,
            ProductColor,
            ProductSize,
            Reservation,
            StoreSetting,
            User,
        )
    except ImportError:
        from database.models import (
            AdminUser,
            Cart,
            CartItem,
            Category,
            Order,
            OrderItem,
            Payment,
            Product,
            ProductColor,
            ProductSize,
            Reservation,
            StoreSetting,
            User,
        )

    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
