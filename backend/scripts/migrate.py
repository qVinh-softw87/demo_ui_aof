from backend.app.db.sqlite import initialize_database
from backend.app.core.config import get_settings


def main() -> None:
    initialize_database()
    print(f"Database initialized at {get_settings().db_path}")


if __name__ == "__main__":
    main()
