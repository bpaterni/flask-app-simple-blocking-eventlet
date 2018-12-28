import os
import urllib
import time

if os.environ.get('ENABLE_MONKEY_PATCH_ALL', None):
    import eventlet
    eventlet.monkey_patch()
    print('monkey patched!')

import cx_Oracle

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from flask import Flask
from flask_socketio import SocketIO

app       = Flask(__name__)
socketio  = SocketIO(app)

db_engine_oracle = create_engine("""oracle+cx_oracle://{}:{}@(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)(HOST={})(PORT={})))(CONNECT_DATA=(SERVICE_NAME={})(SERVER=DEDICATED)))""".format(
                urllib.parse.quote_plus(os.environ['ORACLE_USER']),
                urllib.parse.quote_plus(os.environ['ORACLE_PASS']),
                urllib.parse.quote_plus(os.environ['ORACLE_HOST']),
                urllib.parse.quote_plus(os.environ['ORACLE_PORT']),
                urllib.parse.quote_plus(os.environ['ORACLE_SERVICE_NAME'])),
                connect_args={
                    'mode': cx_Oracle.SYSDBA,
                    })
conn_str_mssql = 'DRIVER={{{}}};SERVER={};DATABASE={};UID={};PWD={}'.format(
    os.environ['MSSQL_DRIVER'],
    os.environ['MSSQL_HOST'],
    os.environ['MSSQL_CATALOG'],
    os.environ['MSSQL_USER'],
    os.environ['MSSQL_PASS'])
db_engine_mssql  = create_engine('mssql+pyodbc:///?odbc_connect={}'.format(urllib.parse.quote_plus(conn_str_mssql)))
db_engine_postgresql = create_engine('postgresql+psycopg2://{}:{}@{}:{}/{}'.format(
    urllib.parse.quote_plus(os.environ['PSQL_USER']),
    urllib.parse.quote_plus(os.environ['PSQL_PASS']),
    urllib.parse.quote_plus(os.environ['PSQL_HOST']),
    urllib.parse.quote_plus(os.environ['PSQL_PORT']),
    urllib.parse.quote_plus(os.environ['PSQL_SCHEMA'])))

db_sessionmaker_oracle = sessionmaker(bind=db_engine_oracle)
db_sessionmaker_mssql  = sessionmaker(bind=db_engine_mssql)
db_sessionmaker_postgresql = sessionmaker(bind=db_engine_postgresql)

@app.route('/api/test')
def api_test(*args, **kwargs):
    return 'api/test: done\n'

@app.route('/api/busy/cpu')
def api_busy(*args, **kwargs):
    print('pre busy')
    time.sleep(15)
    print('post busy')
    return 'busy: done\n'

@app.route('/api/busy/oracle')
def api_busy_oracle(*args, **kwargs):
    print('pre busy oracle')
    sess_oracle = db_sessionmaker_oracle()
    recs = sess_oracle.execute("""
        with x as (select rownum-1 r from dual connect by rownum <= 10)
        select ones.r + 10*tens.r + 100*hundreds.r + 1000*thousands.r n
        from x ones, x tens, x hundreds, x thousands
        order by 1""")
    print(', '.join(str(x[0]) for x in recs.fetchall()[:10]))
    print('post busy oracle')
    return 'busy-oracle: done\n'

@app.route('/api/busy/mssql')
def api_busy_mssql(*args, **kwargs):
    print('pre busy mssql')
    sess_mssql = db_sessionmaker_mssql()
    recs = sess_mssql.execute("""
        WITH x AS (SELECT n FROM (VALUES (0),(1),(2),(3),(4),(5),(6),(7),(8),(9)) v(n))
        SELECT ones.n + 10*tens.n + 100*hundreds.n + 1000*thousands.n + 10000*tenthous.n + 100000*hunthous.n + 1000000*mil.n n
        FROM x ones,     x tens,      x hundreds,       x thousands, x tenthous, x hunthous, x mil
        ORDER BY 1""")
    print(', '.join(str(x[0]) for x in recs.fetchall()[:10]))
    print('post busy mssql')
    return 'busy-mssql: done\n'

@app.route('/api/busy/postgresql')
def api_busy_postgresql(*args, **kwargs):
    print('pre busy postgresql')
    sess_psql = db_sessionmaker_postgresql()
    recs = sess_psql.execute("""SELECT * FROM generate_series(1,10000000)""")
    print(', '.join(str(x[0]) for x in recs.fetchall()[:10]))
    print('post busy postgresql')
    return 'busy-postgresql: done\n'
