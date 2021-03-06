import os

if os.environ.get("ENABLE_MONKEY_PATCH_ALL", None):
    import eventlet

    eventlet.monkey_patch()
    print("monkey patched!")

import inspect
import itertools
import urllib
import time
import cx_Oracle
import eventlet.db_pool
import pyodbc
import traceback

import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from flask import Flask
from flask_socketio import SocketIO

from toolz.curried import concat

app = Flask(__name__)
if not os.environ.get("ASYNC_MODE_THREADING"):
    socketio = SocketIO(app)
else:
    socketio = SocketIO(app, async_mode="threading")

if os.environ.get("ENABLE_DEBUG", None):
    import pdb

    pdb.set_trace()


class ConnectionPoolWrappedDefaultCons(eventlet.db_pool.ConnectionPool):
    def __init__(self, db_module, *args, **kwargs):
        super_pos_defaults = {
            k: v.default
            for k, v in inspect.signature(
                super(ConnectionPoolWrappedDefaultCons, self,).__init__
            ).parameters.items()
            if (
                v.kind
                in (
                    inspect.Parameter.POSITIONAL_ONLY,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                )
                and v.default is not inspect.Parameter.empty
            )
        }
        min_size = kwargs.pop("min_size", super_pos_defaults.get("min_size", 0))
        max_size = kwargs.pop("max_size", super_pos_defaults.get("max_size", 4))
        max_idle = kwargs.pop("max_idle", super_pos_defaults.get("max_idle", 10))
        max_age = kwargs.pop("max_age", super_pos_defaults.get("max_age", 30))
        connect_timeout = kwargs.pop(
            "connect_timeout", super_pos_defaults.get("connect_timeout", 5)
        )
        cleanup = kwargs.pop(
            "cleanup",
            super_pos_defaults.get("cleanup", eventlet.db_pool.cleanup_rollback),
        )

        super(ConnectionPoolWrappedDefaultCons, self).__init__(
            db_module,
            min_size,
            max_size,
            max_idle,
            max_age,
            connect_timeout,
            cleanup,
            *args,
            **kwargs
        )


class ConnectionPoolWithoutTime(ConnectionPoolWrappedDefaultCons):
    def create(self):
        return super(ConnectionPoolWithoutTime, self).create()[2]


creator_oracle = ConnectionPoolWithoutTime(
    cx_Oracle,
    os.environ["ORACLE_USER"],
    os.environ["ORACLE_PASS"],
    "{}/{}".format(os.environ["ORACLE_HOST"], os.environ["ORACLE_SID"],),
    mode=cx_Oracle.SYSDBA,
)

cstr_oracle = "oracle+cx_oracle://{}:{}@(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)(HOST={})(PORT={})))(CONNECT_DATA=(SERVICE_NAME={})(SERVER=DEDICATED)))".format(
    urllib.parse.quote_plus(os.environ["ORACLE_USER"]),
    urllib.parse.quote_plus(os.environ["ORACLE_PASS"]),
    urllib.parse.quote_plus(os.environ["ORACLE_HOST"]),
    urllib.parse.quote_plus(os.environ["ORACLE_PORT"]),
    urllib.parse.quote_plus(os.environ["ORACLE_SERVICE_NAME"]),
)

db_engine_oracle = create_engine(cstr_oracle, **{"creator": creator_oracle.create})
conn_str_mssql = "DRIVER={{{}}};SERVER={};DATABASE={};UID={};PWD={}".format(
    os.environ["MSSQL_DRIVER"],
    os.environ["MSSQL_HOST"],
    os.environ["MSSQL_CATALOG"],
    os.environ["MSSQL_USER"],
    os.environ["MSSQL_PASS"],
)
cstr = "mssql+pyodbc:///?odbc_connect={}".format(
    urllib.parse.quote_plus(conn_str_mssql)
)

mssql_creator = ConnectionPoolWithoutTime(
    pyodbc,
    "DRIVER={{{}}};SERVER={};DATABASE={};UID={};PWD={{{}}}".format(
        os.environ["MSSQL_DRIVER"],
        os.environ["MSSQL_HOST"],
        os.environ["MSSQL_CATALOG"],
        os.environ["MSSQL_USER"],
        os.environ["MSSQL_PASS"],
    ),
)

if not os.environ.get("MSSQL_USE_CUSTOM_EVENTLET_POOL_CREATOR"):
    db_engine_mssql = create_engine(cstr)
else:
    print("Using custom eventlet eventlet pool creator")
    db_engine_mssql = create_engine(
        cstr, **{"creator": mssql_creator.create}, max_overflow=-1
    )
db_engine_postgresql = create_engine(
    "postgresql+psycopg2://{}:{}@{}:{}/{}".format(
        urllib.parse.quote_plus(os.environ["PSQL_USER"]),
        urllib.parse.quote_plus(os.environ["PSQL_PASS"]),
        urllib.parse.quote_plus(os.environ["PSQL_HOST"]),
        urllib.parse.quote_plus(os.environ["PSQL_PORT"]),
        urllib.parse.quote_plus(os.environ["PSQL_SCHEMA"]),
    )
)

db_sessionmaker_oracle = sessionmaker(bind=db_engine_oracle)
db_sessionmaker_mssql = sessionmaker(bind=db_engine_mssql)
db_sessionmaker_postgresql = sessionmaker(bind=db_engine_postgresql)


@app.route("/api/test")
def api_test(*args, **kwargs):
    return "api/test: done\n"


@app.route("/api/busy/cpu")
def api_busy(*args, **kwargs):
    print("pre busy")
    socketio.sleep(15)
    print("post busy")
    return "busy: done\n"


def _fetchall_with_sleep(result_proxy):
    while True:
        recs = result_proxy.fetchmany(size=1000)
        if not recs:
            break
        yield recs
        socketio.sleep(0)


def fetchall_with_sleep(result_proxy):
    for x in concat(_fetchall_with_sleep(result_proxy)):
        yield x
        socketio.sleep(0)


@app.route("/api/busy/oracle")
def api_busy_oracle(*args, **kwargs):
    sess_oracle = None
    try:
        print("pre busy oracle")
        sess_oracle = db_sessionmaker_oracle()
        recs = sess_oracle.execute(
            """
            with x as (select rownum-1 r from dual connect by rownum <= 10)
            select ones.r + 10*tens.r + 100*hundreds.r + 1000*thousands.r + 10000*tenthous.r + 100000*hunthous.r + 1000000*mil.r n
            from x ones, x tens, x hundreds, x thousands, x tenthous, x hunthous, x mil
            order by 1"""
        )
        # recs = sess_oracle.execute('select 1 as n from dual')
        print(
            ", ".join(
                str(x[0]) for x in itertools.islice(fetchall_with_sleep(recs), 10)
            )
        )
        print("post busy oracle")
        return "busy-oracle: done\n"
    except sqlalchemy.exc.TimeoutError as ex:
        print(ex)
        return traceback.format_exc()
    finally:
        if sess_oracle:
            sess_oracle.close()


@app.route("/api/busy/mssql")
def api_busy_mssql(*args, **kwargs):
    sess_mssql = None
    try:
        print("pre busy mssql")
        sess_mssql = db_sessionmaker_mssql()
        recs = sess_mssql.execute(
            """
            WITH x AS (SELECT n FROM (VALUES (0),(1),(2),(3),(4),(5),(6),(7),(8),(9)) v(n))
            SELECT ones.n + 10*tens.n + 100*hundreds.n + 1000*thousands.n + 10000*tenthous.n + 100000*hunthous.n + 1000000*mil.n n
            FROM x ones,     x tens,      x hundreds,       x thousands, x tenthous, x hunthous, x mil
            ORDER BY 1"""
        )
        # recs = sess_mssql.execute('select 1 as n')
        print(
            ", ".join(
                str(x[0]) for x in itertools.islice(fetchall_with_sleep(recs), 10)
            )
        )
        print("post busy mssql")
        return "busy-mssql: done\n"
    except sqlalchemy.exc.TimeoutError as ex:
        print(ex)
        return traceback.format_exc()
    finally:
        if sess_mssql:
            sess_mssql.close()


@app.route("/api/busy/postgresql")
def api_busy_postgresql(*args, **kwargs):
    sess_psql = None
    try:
        print("pre busy postgresql")
        sess_psql = db_sessionmaker_postgresql()
        recs = sess_psql.execute("""SELECT * FROM generate_series(1,10000000)""")
        #print(", ".join(str(x[0]) for x in recs.fetchall()[:10]))
        print(", ".join(
            str(x[0]) for x in itertools.islice(fetchall_with_sleep(recs), 10)
        ))
        print("post busy postgresql")
        return "busy-postgresql: done\n"
    except sqlalchemy.exc.TimeoutError as ex:
        print(ex)
        #return traceback.format_exc()
        return str(ex)
    finally:
        if sess_psql:
            sess_psql.close()


if __name__ == "__main__":
    run_kw = {"use_reloader": os.environ.get("FLASK_USE_RELOADER", False)}
    if os.environ.get("FLASK_HOST"):
        run_kw["host"] = os.environ.get("FLASK_HOST")
    if os.environ.get("FLASK_PORT"):
        run_kw["port"] = os.environ.get("FLASK_PORT")
    socketio.run(app, **run_kw)
