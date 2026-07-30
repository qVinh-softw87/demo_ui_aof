import os

if os.environ.get("DATABASE_URL"):
    from backend.app.db.postgres import get_connection, initialize_database, upsert_asset_products, fetch_asset_products, fetch_asset_product, restrict_mock_products, restrict_products_by_source
else:
    from backend.app.db.sqlite import get_connection, initialize_database, upsert_asset_products, fetch_asset_products, fetch_asset_product, restrict_mock_products, restrict_products_by_source

__all__ = ["get_connection", "initialize_database", "upsert_asset_products", "fetch_asset_products", "fetch_asset_product", "restrict_mock_products", "restrict_products_by_source"]
