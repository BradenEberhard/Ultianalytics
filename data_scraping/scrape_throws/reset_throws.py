import bitdotio
import pandas as pd
from sqlalchemy import create_engine

throws_df = pd.read_csv('/Users/bradeneberhard/Ultianalytics/data_csv/throws.csv')

client = bitdotio.bitdotio("3FyyZ_btR4zfaUfE6NfXcbZijAB8h")


drop_query ='DROP TABLE IF EXISTS "BradenEberhard/Ultianalytics"."throws"'

with client.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute(drop_query)

engine = create_engine('postgresql://BradenEberhard_demo_db_connection:3mXvZ_aMfTQfifHVw6MGk9ihgpZPc@db.bit.io?sslmode=prefer')
throws_df.to_sql('BradenEberhard/Ultianalytics"."throws', engine)
