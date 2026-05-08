import asyncio
import asyncpg
from app.config import get_settings

print('SETTINGS_DB=', get_settings().database_url)

async def f():
    conn = await asyncpg.connect('postgresql://rozgaar:rozgaar@postgres:5432/rozgaar')
    rows = await conn.fetch('select table_schema,table_name from information_schema.tables where table_schema=$1','public')
    txt = 'ROWS=' + repr(rows) + '\n'
    open('/app/tmp_tables.txt','w').write(txt)
    print(txt)
    await conn.close()

asyncio.run(f())
