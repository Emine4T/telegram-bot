try:
    from ehd_shope.database.database import ensure_indexes
except ImportError:
    from database.database import ensure_indexes


def run_migrations() -> None:
    ensure_indexes()
    print("MongoDB indexes initialized.")


if __name__ == "__main__":
    run_migrations()
