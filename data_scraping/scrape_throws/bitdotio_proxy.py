import csv
from io import StringIO
import pandas as pd
from sqlalchemy import create_engine


# Define your username and PostgreSQL connection string here
USERNAME = 'BradenEberhard'
PG_STRING = 'postgresql://BradenEberhard:v2_3tZaS_7n6m4e2Hm3RYiwgJUGx66x4@db.bit.io/BradenEberhard/Ultianalytics'

def psql_insert_copy(table, conn, keys, data_iter):
    """
    Execute SQL statement inserting data

    Parameters
    ----------
    table : pandas.io.sql.SQLTable
    conn : sqlalchemy.engine.Engine or sqlalchemy.engine.Connection
    keys : list of str
        Column names
    data_iter : Iterable that iterates the values to be inserted
    """
    # gets a DBAPI connection that can provide a cursor
    dbapi_conn = conn.connection
    with dbapi_conn.cursor() as cur:
        s_buf = StringIO()
        writer = csv.writer(s_buf)
        writer.writerows(data_iter)
        s_buf.seek(0)

        columns = ', '.join(f'"{k}"' for k in keys)
        table_name = f'"{table.schema}"."{table.name}"'
        sql = f'COPY {table_name} ({columns}) FROM STDIN WITH CSV'
        cur.copy_expert(sql=sql, file=s_buf)


def insert_table(df, table_name):
    df = pd.DataFrame(df)
    # Create SQLAlchemy engine to manage our database connections
    # Note that we bump the statement_timeout to 60 seconds
    engine = create_engine(PG_STRING)
    # SQL for querying an entire table
    with engine.connect() as conn:
        df.to_sql(
            table_name,
            conn,
            schema=f"{USERNAME}/Ultianalytics",
            index=False,
            if_exists='replace',
            method=psql_insert_copy)