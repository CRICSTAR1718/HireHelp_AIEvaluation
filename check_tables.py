import psycopg

conn = psycopg.connect(
    "postgresql://postgres.evujknkpkcrgmgiwxgbb:cricstar1718@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres"
)
tables = [r[0] for r in conn.execute(
    "SELECT tablename FROM pg_tables WHERE schemaname='public'"
).fetchall()]
print(tables)