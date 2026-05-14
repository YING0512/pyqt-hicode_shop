from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLabel, QHBoxLayout, QMessageBox, QHeaderView, QSpinBox)
from PyQt5.QtCore import Qt
from db_cloud import get_connection

class TabCart(QWidget):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # 標題與重新整理按鈕
        header_layout = QHBoxLayout()
        title = QLabel("🛒 我的購物車")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(title)
        
        btn_refresh = QPushButton("🔄 重新整理")
        btn_refresh.clicked.connect(self.load_cart)
        header_layout.addWidget(btn_refresh, alignment=Qt.AlignRight)
        layout.addLayout(header_layout)

        # 購物車表格
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["商品名稱", "單價", "數量", "小計"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        # 總金額與結帳
        bottom_layout = QHBoxLayout()
        self.lbl_total = QLabel("總計: $0.00")
        self.lbl_total.setStyleSheet("font-size: 18px; font-weight: bold; color: #e74c3c;")
        bottom_layout.addWidget(self.lbl_total)
        
        self.btn_checkout = QPushButton("💳 前往結帳")
        self.btn_checkout.setStyleSheet("background-color: #27ae60; color: white; padding: 10px; font-weight: bold;")
        self.btn_checkout.clicked.connect(self.checkout)
        bottom_layout.addWidget(self.btn_checkout, alignment=Qt.AlignRight)
        layout.addLayout(bottom_layout)

        self.setLayout(layout)

    def load_cart(self):
        conn = get_connection()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            # 關聯查詢購物車商品
            query = """
                SELECT p.name, p.price, ci.quantity, (p.price * ci.quantity) as subtotal, ci.cart_item_id
                FROM Cart c
                JOIN CartItem ci ON c.cart_id = ci.cart_id
                JOIN Product p ON ci.product_id = p.product_id
                WHERE c.user_id = ?
            """
            cursor.execute(query, (self.user_id,))
            items = cursor.fetchall()
            
            self.table.setRowCount(len(items))
            total_sum = 0.0
            
            for row_idx, item in enumerate(items):
                name, price, qty, subtotal, cart_item_id = item
                total_sum += float(subtotal)
                
                self.table.setItem(row_idx, 0, QTableWidgetItem(name))
                self.table.setItem(row_idx, 1, QTableWidgetItem(f"${price:.2f}"))
                
                spin_box = QSpinBox()
                spin_box.setMinimum(1)
                spin_box.setMaximum(999) # 可以根據實際庫存設定上限，此處暫設為999
                spin_box.setValue(int(qty))
                # 使用 lambda 捕捉當下的 cart_item_id
                spin_box.valueChanged.connect(lambda val, ci_id=cart_item_id: self.update_quantity(ci_id, val))
                self.table.setCellWidget(row_idx, 2, spin_box)
                
                self.table.setItem(row_idx, 3, QTableWidgetItem(f"${subtotal:.2f}"))
            
            self.lbl_total.setText(f"總計: ${total_sum:.2f}")
            self.btn_checkout.setEnabled(total_sum > 0)
            
        except Exception as e:
            QMessageBox.critical(self, "載入失敗", f"無法載入購物車: {e}")
        finally:
            conn.close()

    def update_quantity(self, cart_item_id, new_quantity):
        conn = get_connection()
        if not conn: return
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE CartItem SET quantity = ? WHERE cart_item_id = ?", (new_quantity, cart_item_id))
            conn.commit()
            self.load_cart() # 重新載入以更新小計和總計
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"更新數量失敗: {e}")
        finally:
            conn.close()

    def checkout(self):
        # 防呆
        reply = QMessageBox.question(self, '確認結帳', '您確定要進行結帳嗎？', 
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes: return

        conn = get_connection()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            
            # 1. 計算總額並獲取購物車與會員資訊
            cursor.execute("SELECT cart_id FROM Cart WHERE user_id = ?", (self.user_id,))
            cart = cursor.fetchone()
            if not cart: return
            cart_id = cart[0]
            
            # 撈取購物車中商品的詳細資訊，包含 seller_id 以便撥款
            query = """
                SELECT p.product_id, p.price, ci.quantity, p.seller_id
                FROM CartItem ci
                JOIN Product p ON ci.product_id = p.product_id
                WHERE ci.cart_id = ?
            """
            cursor.execute(query, (cart_id,))
            items = cursor.fetchall()
            
            if not items:
                QMessageBox.warning(self, "警告", "購物車是空的！")
                return
                
            total_amount = sum(float(item[1]) * int(item[2]) for item in items)
            
            # 2. 檢查買家錢包餘額
            cursor.execute("SELECT wallet_balance FROM User WHERE user_id = ?", (self.user_id,))
            balance = cursor.fetchone()[0]
            if balance is None: balance = 0.0
            
            if float(balance) < total_amount:
                QMessageBox.warning(self, "餘額不足", f"結帳需要 ${total_amount:.2f}，但您的錢包只有 ${balance:.2f}。\n請先至錢包儲值 (請使用兌換碼)！")
                return
                
            # 3. 扣款與建立訂單
            # 3.1 從買家錢包扣除總額
            new_balance = float(balance) - total_amount
            cursor.execute("UPDATE User SET wallet_balance = ? WHERE user_id = ?", (new_balance, self.user_id))
            
            # 3.2 建立訂單主檔
            cursor.execute("INSERT INTO \"Order\" (user_id, total_amount, status, shipping_address) VALUES (?, ?, 'PENDING', '預設地址')", 
                           (self.user_id, total_amount))
            order_id = cursor.lastrowid
            
            # 4. 寫入訂單明細、撥款給賣家、並清空購物車
            for item in items:
                pid, price, qty, seller_id = item
                subtotal = float(price) * int(qty)
                
                # 4.1 撥款給賣家：將該商品的總額加入賣家的錢包
                if seller_id is not None:
                    cursor.execute("UPDATE User SET wallet_balance = wallet_balance + ? WHERE user_id = ?", (subtotal, seller_id))
                
                # 4.2 寫入訂單明細
                cursor.execute("INSERT INTO OrderItem (order_id, product_id, quantity, price_snapshot) VALUES (?, ?, ?, ?)",
                               (order_id, pid, qty, price))
                               
                # 4.3 扣除商品庫存
                cursor.execute("UPDATE Product SET stock_quantity = stock_quantity - ? WHERE product_id = ?", (qty, pid))
            
            # 4.4 結帳完畢後清空購物車明細
            cursor.execute("DELETE FROM CartItem WHERE cart_id = ?", (cart_id,))
            
            conn.commit()
            QMessageBox.information(self, "結帳成功", f"結帳成功！已扣款 ${total_amount:.2f}。您的訂單編號為: #{order_id}")
            self.load_cart()
            
        except Exception as e:
            QMessageBox.critical(self, "結帳失敗", f"發生錯誤: {e}")
        finally:
            conn.close()
