import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_cloud import get_connection

conn = get_connection()
if conn:
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE Product SET is_deleted = 1, status = 'off_shelf' WHERE product_id IN (1, 2, 3, 4)")
        conn.commit()
        print("商品 1, 2, 3, 4 刪除成功！")
    except Exception as e:
        print("刪除失敗:", e)
    finally:
        conn.close()
