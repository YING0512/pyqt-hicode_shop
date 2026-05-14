from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLabel, QHBoxLayout, QMessageBox, QHeaderView)
from PyQt5.QtCore import Qt
from db_cloud import get_connection

class TabProducts(QWidget):
    """
    商品商城頁籤類別
    負責展示所有賣家上架的商品，並提供買家將商品「加入購物車」的功能。
    """
    def __init__(self, user_id):
        super().__init__()
        # 紀錄目前操作的買家 ID
        self.user_id = user_id
        self.init_ui()
        self.load_products()

    def init_ui(self):
        """初始化商品列表介面"""
        layout = QVBoxLayout()
        
        # 標題與重新整理按鈕的水平佈局
        header_layout = QHBoxLayout()
        lbl_title = QLabel("🛍️ 最新商品列表")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2980b9;")
        header_layout.addWidget(lbl_title)
        
        btn_refresh = QPushButton("🔄 重新整理")
        btn_refresh.clicked.connect(self.load_products)
        header_layout.addWidget(btn_refresh, alignment=Qt.AlignRight)
        
        layout.addLayout(header_layout)

        # 建立商品清單的表格 (QTableWidget)
        self.table = QTableWidget()
        # 設定表格共有 4 個欄位
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["商品名稱", "價格", "庫存", "操作"])
        
        # 設定所有欄位自動拉伸以填滿空白區域
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        self.setLayout(layout)

    def load_products(self):
        """
        從雲端資料庫載入最新商品列表。
        只會撈取狀態為「上架中 (on_shelf)」且「未被軟刪除 (is_deleted=0)」的商品。
        """
        conn = get_connection()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            # 確保買家只看得到上架中且未被刪除的商品
            cursor.execute("""
                SELECT product_id, name, price, stock_quantity 
                FROM Product 
                WHERE is_deleted = 0 AND status = 'on_shelf'
                ORDER BY product_id DESC
            """)
            products = cursor.fetchall()
            
            # 設定表格的列數與撈到的商品數量一致
            self.table.setRowCount(len(products))
            for row_idx, product in enumerate(products):
                p_id, name, price, stock = product
                
                # 填入文字資料
                # self.table.setItem(row_idx, 0, QTableWidgetItem(str(p_id)))
                self.table.setItem(row_idx, 0, QTableWidgetItem(name))
                self.table.setItem(row_idx, 1, QTableWidgetItem(f"${float(price):.2f}"))
                self.table.setItem(row_idx, 2, QTableWidgetItem(str(stock)))
                
                # 在第五個欄位動態建立「加入購物車」按鈕
                btn_add_cart = QPushButton("🛒 加入購物車")
                btn_add_cart.setStyleSheet("background-color: #f39c12; color: white; border-radius: 3px;")
                # 使用 lambda 函式綁定當前商品的 p_id
                btn_add_cart.clicked.connect(lambda checked, pid=p_id: self.add_to_cart(pid))
                self.table.setCellWidget(row_idx, 3, btn_add_cart)
                
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"載入商品失敗: {e}")
        finally:
            conn.close()

    def add_to_cart(self, product_id):
        """
        將選定的商品加入購物車。
        
        參數:
            product_id (int): 被點擊的商品 ID
        """
        conn = get_connection()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            
            # 1. 確保目前使用者擁有一台專屬的購物車 (如果沒有則建立)
            cursor.execute("SELECT cart_id FROM Cart WHERE user_id = ?", (self.user_id,))
            cart = cursor.fetchone()
            if not cart:
                cursor.execute("INSERT INTO Cart (user_id) VALUES (?)", (self.user_id,))
                cart_id = cursor.lastrowid
            else:
                cart_id = cart[0]
                
            # 2. 檢查該商品是否已經在購物車內
            cursor.execute("SELECT quantity FROM CartItem WHERE cart_id = ? AND product_id = ?", (cart_id, product_id))
            item = cursor.fetchone()
            
            if item:
                # 若已存在，則數量 + 1
                cursor.execute("UPDATE CartItem SET quantity = quantity + 1 WHERE cart_id = ? AND product_id = ?", (cart_id, product_id))
            else:
                # 若不存在，則新增該商品至購物車明細，預設數量為 1
                cursor.execute("INSERT INTO CartItem (cart_id, product_id, quantity) VALUES (?, ?, 1)", (cart_id, product_id))
                
            conn.commit()
            QMessageBox.information(self, "成功", "商品已加入購物車！")
            
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"加入購物車失敗: {e}")
        finally:
            conn.close()
