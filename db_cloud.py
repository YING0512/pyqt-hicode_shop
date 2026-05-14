import sqlitecloud
import hashlib
import os
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數，將隱私資訊與程式碼分離
load_dotenv()

# ==========================================
# 資料庫連線字串 (Connection String)
# 為了安全性，此連線字串與 API Key 已被抽離至 .env 檔案中進行保護 (加密/隱藏)
# ==========================================
CONNECTION_STRING = os.getenv("SQLITE_CLOUD_URL")

# 防呆機制：若未正確設定環境變數，則在終端機發出警告
if not CONNECTION_STRING:
    print("警告：無法從 .env 檔案讀取到 SQLITE_CLOUD_URL！請確認 .env 檔案是否存在。")

# 指定要操作的資料庫名稱
DATABASE_NAME = "hicode_shop_db"  # 若您當初建立的資料庫名稱不同，請修改這裡

def get_connection():
    """
    取得與 SQLite Cloud 雲端資料庫的連線物件。
    
    回傳:
        conn (Connection): 成功時回傳連線物件，失敗則回傳 None。
    """
    try:
        # 使用 sqlitecloud 套件建立連線
        conn = sqlitecloud.connect(CONNECTION_STRING)
        # SQLite Cloud 特有語法：需要明確指定操作哪一個資料庫
        conn.execute(f"USE DATABASE {DATABASE_NAME}")
        return conn
    except Exception as e:
        print(f"資料庫連線發生錯誤: {e}")
        return None

def hash_password(password):
    """
    密碼雜湊處理函數
    為了保護使用者密碼，我們嚴禁在資料庫中儲存「明文密碼」。
    此函數會將密碼字串轉換為不可逆的 SHA-256 雜湊值。
    
    參數:
        password (str): 使用者輸入的原始密碼
    回傳:
        str: 經過 SHA-256 雜湊後的 64 字元字串
    """
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def ensure_schema_updated():
    """
    資料庫結構自動升級機制 (Auto Migration)
    確保資料庫擁有專案後期所新增的各項欄位與表格 (例如錢包餘額、權限角色、兌換碼、賣家商品等)。
    每次啟動程式時都會執行一次，以確保資料庫結構與程式碼相容。
    """
    conn = get_connection()
    if not conn: return
    try:
        cursor = conn.cursor()
        
        # 1. 檢查 User 表格是否有 wallet_balance 與 role 欄位
        cursor.execute("PRAGMA table_info(User)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'wallet_balance' not in columns:
            print("正在為 User 資料表補上 wallet_balance 欄位...")
            cursor.execute("ALTER TABLE User ADD COLUMN wallet_balance DECIMAL(10, 2) DEFAULT 0.00")
            
        if 'role' not in columns:
            print("正在為 User 資料表補上 role 欄位...")
            cursor.execute("ALTER TABLE User ADD COLUMN role VARCHAR(20) DEFAULT 'user'")
            
            # (彩蛋/隱藏功能) 系統初始化時，自動將第一位註冊者，或是名稱為 "admin" 的人設為最高權限管理員
            cursor.execute("UPDATE User SET role = 'admin' WHERE user_id = 1 OR username = 'admin'")

        # 2. 建立 RedemptionCode 表格 (用於儲存兌換碼的基本資訊與限制)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS RedemptionCode (
                code_id INTEGER PRIMARY KEY AUTOINCREMENT,
                code VARCHAR(50) NOT NULL UNIQUE,          -- 兌換碼字串 (必須唯一)
                value DECIMAL(10, 2) NOT NULL,             -- 兌換面額
                max_uses INTEGER NOT NULL DEFAULT 1,       -- 總共可被領取的次數上限
                current_uses INTEGER NOT NULL DEFAULT 0,   -- 目前已經被領取的次數
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 3. 建立 RedemptionHistory 表格 (用於防呆，紀錄誰已經領過哪個代碼，防止重複領取)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS RedemptionHistory (
                history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                code_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                redeemed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (code_id) REFERENCES RedemptionCode(code_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES User(user_id) ON DELETE CASCADE,
                UNIQUE(code_id, user_id)                   -- 聯合唯一鍵：同一個代碼，同一個人只能領一次
            )
        """)
        
        # 4. 檢查 Product 表格是否有「賣家中心」所需的進階欄位
        cursor.execute("PRAGMA table_info(Product)")
        product_columns = [row[1] for row in cursor.fetchall()]
        
        if 'seller_id' not in product_columns:
            print("正在為 Product 資料表補上 seller_id 欄位...")
            cursor.execute("ALTER TABLE Product ADD COLUMN seller_id INTEGER")
            
        if 'status' not in product_columns:
            print("正在為 Product 資料表補上 status 欄位...")
            cursor.execute("ALTER TABLE Product ADD COLUMN status VARCHAR(20) DEFAULT 'on_shelf'")
            
        if 'is_deleted' not in product_columns:
            print("正在為 Product 資料表補上 is_deleted 欄位...")
            cursor.execute("ALTER TABLE Product ADD COLUMN is_deleted INTEGER DEFAULT 0")

        # 5. 確保 Category (分類) 表格至少有預設的初始資料，避免賣家無法選擇商品分類
        cursor.execute("SELECT COUNT(*) FROM Category")
        if cursor.fetchone()[0] == 0:
            print("正在初始化商品分類資料...")
            cursor.execute("INSERT INTO Category (category_name) VALUES ('3C 電子產品'), ('書籍文具'), ('服飾與配件'), ('生活家電')")
            
        # 6. 檢查 Order 表格是否有 cancellation_reason 欄位 (用於買賣家取消訂單)
        cursor.execute("PRAGMA table_info(\"Order\")")
        order_columns = [row[1] for row in cursor.fetchall()]
        if 'cancellation_reason' not in order_columns:
            print("正在為 Order 資料表補上 cancellation_reason 欄位...")
            cursor.execute("ALTER TABLE \"Order\" ADD COLUMN cancellation_reason TEXT")
            
        if 'rejection_reason' not in order_columns:
            print("正在為 Order 資料表補上 rejection_reason 欄位...")
            cursor.execute("ALTER TABLE \"Order\" ADD COLUMN rejection_reason TEXT")
            
        # 提交所有的資料庫結構變更
        conn.commit()
    except Exception as e:
        print(f"更新資料庫結構時發生錯誤: {e}")
    finally:
        # 確保連線正常關閉，釋放資源
        conn.close()
