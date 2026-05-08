import asyncio
import pkgutil
import importlib
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import get_settings
from app.db.base import Base

# import all submodules in app.db.models so mapped classes register
import app.db.models as models_pkg
for finder, name, ispkg in pkgutil.iter_modules(models_pkg.__path__):
    importlib.import_module(f"{models_pkg.__name__}.{name}")

async def main():
    settings = get_settings()
    print('SETTINGS_DB =', settings.database_url)
    engine = create_async_engine(settings.database_url, echo=True)
    async with engine.begin() as conn:
        ver = await conn.execute(text('select current_database(), current_schema()'))
        print('PG INFO =', ver.fetchall())
        print('Running Base.metadata.create_all via async engine...')
        await conn.run_sync(Base.metadata.create_all)
        print('CREATE_ALL completed')
        rows = await conn.execute(text("select table_schema,table_name from information_schema.tables where table_schema='public' order by table_name"))
        print('TABLES =', rows.fetchall())
    await engine.dispose()

if __name__ == '__main__':
    asyncio.run(main())
