from backend.app.core.config import get_settings
from backend.app.data.mock_asset_products import load_mock_asset_products
from backend.app.db.sqlite import fetch_asset_products, initialize_database, upsert_asset_products


def main() -> None:
    settings = get_settings()
    initialize_database()
    existing = fetch_asset_products(approved_only=False)
    if existing:
        print(
            f"Skipped mock seed: {len(existing)} asset products already exist in "
            f"{settings.db_path}"
        )
        return
    products = load_mock_asset_products(settings.data_dir)
    count = upsert_asset_products(products)
    print(f"Seeded {count} mock asset products into {settings.db_path}")


if __name__ == "__main__":
    main()
