from app.core.db import engine
from sqlalchemy import text

with engine.begin() as conn:
    conn.execute(text('DROP TABLE IF EXISTS alembic_version'))
    print("alembic_version table dropped successfully!") 