import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
conn = psycopg.connect(os.environ["DATABASE_URL_MIGRATIONS"])
conn.execute("DROP TABLE IF EXISTS alembic_version")
conn.commit()
print("alembic_version table dropped")