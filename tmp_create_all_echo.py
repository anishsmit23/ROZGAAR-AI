from app.config import get_settings
from app.db.base import Base
from sqlalchemy import create_engine, text

def main():
    url = get_settings().database_url
    print('SETTINGS_DB =', url)
    sync_url = url.replace('+asyncpg', '')
    print('SYNC_URL =', sync_url)

    engine = create_engine(sync_url, echo=True)
    with engine.connect() as conn:
        ver = conn.execute(text('select version();')).fetchone()
        print('PG VERSION =', ver)
        print('Running Base.metadata.create_all() with echo...')
        Base.metadata.create_all(bind=conn)
        rows = conn.execute(text("select table_schema,table_name from information_schema.tables where table_schema='public' order by table_name")).fetchall()
        print('TABLES_AFTER_CREATE_ALL =', rows)

if __name__ == '__main__':
    main()
