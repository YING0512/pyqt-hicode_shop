import sqlitecloud
import os
from dotenv import load_dotenv

load_dotenv()
conn = sqlitecloud.connect(os.getenv("SQLITE_CLOUD_URL"))
conn.execute("USE DATABASE hicode_shop_db")
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(\"Order\")")
print("Order Schema:", cursor.fetchall())
cursor.execute("PRAGMA table_info(OrderItem)")
print("OrderItem Schema:", cursor.fetchall())
conn.close()
