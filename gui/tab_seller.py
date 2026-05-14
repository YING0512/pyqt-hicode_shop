from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLineEdit, 
                             QPushButton, QLabel, QHBoxLayout, QMessageBox, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QComboBox, QTabWidget, QInputDialog)
from PyQt5.QtCore import Qt
from db_cloud import get_connection

class TabSeller(QWidget):
    """
    賣家中心頁籤類別
    提供給具有 seller 或 admin 權限的使用者，包含「商品管理」與「訂單管理」兩大功能。
    """
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.init_ui()

    def init_ui(self):
        """初始化賣家中心介面 (包含子頁籤)"""
        layout = QVBoxLayout()
        
        # 標題
        title = QLabel("🏪 賣家中心")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2980b9; margin-bottom: 10px;")
        layout.addWidget(title)

        # 建立子頁籤
        self.tabs = QTabWidget()
        
        # 1. 商品管理子頁籤
        self.tab_products = QWidget()
        self.init_products_tab()
        self.tabs.addTab(self.tab_products, "📦 商品管理")
        
        # 2. 訂單管理子頁籤
        self.tab_orders = QWidget()
        self.init_orders_tab()
        self.tabs.addTab(self.tab_orders, "📋 訂單管理")

        self.tabs.currentChanged.connect(self.on_tab_changed)
        layout.addWidget(self.tabs)
        self.setLayout(layout)

    # ==========================================
    # 商品管理 (Product Management) 區塊
    # ==========================================
    def init_products_tab(self):
        layout = QVBoxLayout(self.tab_products)
        
        # 上架商品區塊
        form_layout = QFormLayout()
        
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("請輸入商品名稱")
        form_layout.addRow("📦 商品名稱:", self.input_name)
        
        self.input_desc = QLineEdit()
        self.input_desc.setPlaceholderText("請輸入商品描述")
        form_layout.addRow("📝 商品描述:", self.input_desc)
        
        self.input_price = QLineEdit()
        self.input_price.setPlaceholderText("請輸入價格 (例如: 100)")
        form_layout.addRow("💰 商品價格:", self.input_price)
        
        self.input_stock = QLineEdit()
        self.input_stock.setPlaceholderText("請輸入庫存數量 (例如: 50)")
        form_layout.addRow("📊 庫存數量:", self.input_stock)
        
        self.combo_category = QComboBox()
        self.load_categories()
        form_layout.addRow("🏷️ 分類:", self.combo_category)

        btn_add = QPushButton("上架新商品")
        btn_add.setStyleSheet("background-color: #27ae60; color: white; padding: 10px; font-weight: bold;")
        btn_add.clicked.connect(self.add_product)
        form_layout.addWidget(btn_add)

        layout.addLayout(form_layout)

        # 列表
        lbl_list = QLabel("📋 我上架的商品列表")
        lbl_list.setStyleSheet("font-weight: bold; margin-top: 20px;")
        layout.addWidget(lbl_list)

        self.table_products = QTableWidget()
        self.table_products.setColumnCount(5)
        self.table_products.setHorizontalHeaderLabels(["ID", "商品名稱", "價格", "庫存", "操作"])
        self.table_products.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table_products)

    def load_categories(self):
        conn = get_connection()
        if not conn: return
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT category_id, category_name FROM Category")
            for cid, cname in cursor.fetchall():
                self.combo_category.addItem(cname, cid)
        except Exception as e:
            print("無法載入分類:", e)
        finally:
            conn.close()

    def load_my_products(self):
        conn = get_connection()
        if not conn: return
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT product_id, name, price, stock_quantity FROM Product WHERE seller_id = ? AND is_deleted = 0 ORDER BY product_id DESC", (self.user_id,))
            products = cursor.fetchall()
            
            self.table_products.setRowCount(len(products))
            for row_idx, product in enumerate(products):
                p_id, name, price, stock = product
                
                self.table_products.setItem(row_idx, 0, QTableWidgetItem(str(p_id)))
                self.table_products.setItem(row_idx, 1, QTableWidgetItem(name))
                self.table_products.setItem(row_idx, 2, QTableWidgetItem(f"${float(price):.2f}"))
                self.table_products.setItem(row_idx, 3, QTableWidgetItem(str(stock)))
                
                btn_del = QPushButton("下架/刪除")
                btn_del.setStyleSheet("background-color: #c0392b; color: white; border-radius: 3px;")
                btn_del.clicked.connect(lambda checked, pid=p_id: self.delete_product(pid))
                self.table_products.setCellWidget(row_idx, 4, btn_del)
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"載入我的商品失敗: {e}")
        finally:
            conn.close()

    def add_product(self):
        name = self.input_name.text().strip()
        desc = self.input_desc.text().strip()
        price_str = self.input_price.text().strip()
        stock_str = self.input_stock.text().strip()
        cat_id = self.combo_category.currentData()

        if not name or not price_str or not stock_str:
            QMessageBox.warning(self, "錯誤", "請填寫商品名稱、價格與庫存！")
            return
        try:
            price = float(price_str)
            stock = int(stock_str)
        except ValueError:
            QMessageBox.warning(self, "錯誤", "價格與庫存必須為數字！")
            return

        conn = get_connection()
        if not conn: return
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO Product (seller_id, name, description, price, stock_quantity, category_id, status)
                VALUES (?, ?, ?, ?, ?, ?, 'on_shelf')
            """, (self.user_id, name, desc, price, stock, cat_id))
            conn.commit()
            QMessageBox.information(self, "成功", "商品上架成功！")
            self.input_name.clear()
            self.input_desc.clear()
            self.input_price.clear()
            self.input_stock.clear()
            self.load_my_products()
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"上架失敗: {e}")
        finally:
            conn.close()

    def delete_product(self, product_id):
        reply = QMessageBox.question(self, '確認', '確定要下架並刪除此商品嗎？', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes: return
        
        conn = get_connection()
        if not conn: return
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE Product SET is_deleted = 1, status = 'off_shelf' WHERE product_id = ? AND seller_id = ?", (product_id, self.user_id))
            conn.commit()
            self.load_my_products()
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"刪除失敗: {e}")
        finally:
            conn.close()


    # ==========================================
    # 訂單管理 (Order Management) 區塊
    # ==========================================
    def init_orders_tab(self):
        layout = QVBoxLayout(self.tab_orders)
        
        header_layout = QHBoxLayout()
        lbl_list = QLabel("📋 顧客購買訂單")
        lbl_list.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(lbl_list)
        
        btn_refresh = QPushButton("🔄 重新整理")
        btn_refresh.clicked.connect(self.load_seller_orders)
        header_layout.addWidget(btn_refresh, alignment=Qt.AlignRight)
        
        layout.addLayout(header_layout)

        self.table_orders = QTableWidget()
        self.table_orders.setColumnCount(6)
        self.table_orders.setHorizontalHeaderLabels(["訂單編號", "買家", "總金額", "狀態", "操作", "備註"])
        self.table_orders.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_orders.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        layout.addWidget(self.table_orders)

    def load_seller_orders(self):
        """撈取包含目前賣家商品的訂單"""
        conn = get_connection()
        if not conn: return
        try:
            cursor = conn.cursor()
            # 找出包含此賣家商品的獨特訂單
            query = """
                SELECT DISTINCT o.order_id, u.username, o.total_amount, o.status, o.cancellation_reason
                FROM "Order" o
                JOIN OrderItem oi ON o.order_id = oi.order_id
                JOIN Product p ON oi.product_id = p.product_id
                JOIN User u ON o.user_id = u.user_id
                WHERE p.seller_id = ?
                ORDER BY o.order_id DESC
            """
            cursor.execute(query, (self.user_id,))
            orders = cursor.fetchall()
            
            self.table_orders.setRowCount(len(orders))
            
            status_map = {
                'PENDING': ('待處理', Qt.black),
                'COMPLETED': ('已完成', Qt.darkGreen),
                'CANCEL_REQUESTED': ('取消申請中', Qt.darkYellow),
                'CANCELLED': ('已取消', Qt.red)
            }
            
            for row_idx, order in enumerate(orders):
                o_id, buyer_name, amount, status, reason = order
                
                self.table_orders.setItem(row_idx, 0, QTableWidgetItem(f"#{o_id}"))
                self.table_orders.setItem(row_idx, 1, QTableWidgetItem(buyer_name))
                self.table_orders.setItem(row_idx, 2, QTableWidgetItem(f"${float(amount):.2f}"))
                
                status_text, color = status_map.get(status, (status, Qt.black))
                if status == 'PENDING' and reason:
                    status_text = '取消申請中'
                    color = Qt.darkYellow
                status_item = QTableWidgetItem(status_text)
                status_item.setForeground(color)
                self.table_orders.setItem(row_idx, 3, status_item)
                
                # 操作按鈕區域
                action_widget = QWidget()
                action_layout = QVBoxLayout(action_widget)
                action_layout.setContentsMargins(5, 4, 5, 4)
                action_layout.setSpacing(8)
                action_layout.setAlignment(Qt.AlignCenter)
                
                if status == 'PENDING' and reason:
                    btn_approve = QPushButton("同意取消")
                    btn_approve.setStyleSheet("background-color: #e67e22; color: white; border-radius: 4px; padding: 6px 12px; font-weight: bold;")
                    btn_approve.clicked.connect(lambda checked, oid=o_id: self.approve_cancellation(oid))
                    action_layout.addWidget(btn_approve)
                    
                    btn_reject = QPushButton("駁回申請")
                    btn_reject.setStyleSheet("background-color: #8e44ad; color: white; border-radius: 4px; padding: 6px 12px; font-weight: bold;")
                    btn_reject.clicked.connect(lambda checked, oid=o_id: self.reject_cancellation(oid))
                    action_layout.addWidget(btn_reject)
                elif status == 'PENDING':
                    btn_complete = QPushButton("完成訂單")
                    btn_complete.setStyleSheet("background-color: #27ae60; color: white; border-radius: 4px; padding: 6px 12px; font-weight: bold;")
                    btn_complete.clicked.connect(lambda checked, oid=o_id: self.complete_order(oid))
                    
                    btn_cancel = QPushButton("直接取消")
                    btn_cancel.setStyleSheet("background-color: #e74c3c; color: white; border-radius: 4px; padding: 6px 12px; font-weight: bold;")
                    btn_cancel.clicked.connect(lambda checked, oid=o_id: self.cancel_order_with_reason(oid))
                    
                    action_layout.addWidget(btn_complete)
                    action_layout.addWidget(btn_cancel)
                    
                self.table_orders.setCellWidget(row_idx, 4, action_widget)
                
                reason_text = f"原因: {reason}" if reason else ""
                self.table_orders.setItem(row_idx, 5, QTableWidgetItem(reason_text))
                
            self.table_orders.resizeRowsToContents()
                
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"載入訂單失敗: {e}")
        finally:
            conn.close()

    def complete_order(self, order_id):
        """將訂單狀態改為已完成"""
        reply = QMessageBox.question(self, '確認', '確定要將此訂單標記為「已完成」嗎？', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes: return
        
        conn = get_connection()
        if not conn: return
        try:
            cursor = conn.cursor()
            cursor.execute('UPDATE "Order" SET status = ? WHERE order_id = ?', ('COMPLETED', order_id))
            conn.commit()
            QMessageBox.information(self, "成功", "訂單已完成！")
            self.load_seller_orders()
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"更新狀態失敗: {e}")
        finally:
            conn.close()

    def cancel_order_with_reason(self, order_id):
        """賣家主動取消訂單，需填寫理由"""
        reason, ok = QInputDialog.getText(self, "取消訂單", f"請輸入直接取消訂單 #{order_id} 的理由:")
        if not ok: return
        reason = reason.strip()
        if not reason:
            QMessageBox.warning(self, "錯誤", "必須填寫取消理由！")
            return
            
        self.execute_cancellation(order_id, reason)

    def approve_cancellation(self, order_id):
        """同意買家的取消申請"""
        reply = QMessageBox.question(self, '確認', '確定要同意取消此筆訂單並全額退款嗎？', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes: return
        
        # 由於是同意買家申請，保留原本的理由或加上前綴
        self.execute_cancellation(order_id, None)

    def reject_cancellation(self, order_id):
        """駁回買家的取消申請"""
        reason, ok = QInputDialog.getText(self, "駁回取消申請", f"請輸入駁回訂單 #{order_id} 取消申請的緣由:")
        if not ok: return
        reason = reason.strip()
        if not reason:
            QMessageBox.warning(self, "錯誤", "必須填寫駁回緣由！")
            return
            
        conn = get_connection()
        if not conn: return
        try:
            cursor = conn.cursor()
            cursor.execute('UPDATE "Order" SET cancellation_reason = NULL, rejection_reason = ? WHERE order_id = ?', (reason, order_id))
            conn.commit()
            QMessageBox.information(self, "成功", "已成功駁回該取消申請！訂單已退回待處理狀態。")
            self.load_seller_orders()
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"駁回失敗: {e}")
        finally:
            conn.close()

    def execute_cancellation(self, order_id, new_reason=None):
        """
        執行整筆訂單取消的完整邏輯 (逆向金流與庫存返還)
        1. 從所有相關賣家扣回入帳金額
        2. 全額退款給買家
        3. 恢復庫存
        4. 狀態改為 CANCELLED
        """
        conn = get_connection()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            
            # 取得訂單資訊 (買家 ID, 總金額)
            cursor.execute('SELECT user_id, total_amount, cancellation_reason FROM "Order" WHERE order_id = ?', (order_id,))
            order_info = cursor.fetchone()
            if not order_info: return
            buyer_id, total_amount, existing_reason = order_info
            
            # 決定取消理由
            final_reason = new_reason if new_reason else existing_reason
            
            # 取得訂單明細，準備退回賣家的款項並恢復庫存
            cursor.execute("""
                SELECT p.seller_id, oi.quantity, oi.price_snapshot, p.product_id
                FROM OrderItem oi
                JOIN Product p ON oi.product_id = p.product_id
                WHERE oi.order_id = ?
            """, (order_id,))
            items = cursor.fetchall()
            
            for item in items:
                seller_id, qty, price, pid = item
                subtotal = float(price) * int(qty)
                
                # 1. 扣回賣家入帳
                if seller_id is not None:
                    cursor.execute("UPDATE User SET wallet_balance = wallet_balance - ? WHERE user_id = ?", (subtotal, seller_id))
                
                # 2. 恢復庫存
                cursor.execute("UPDATE Product SET stock_quantity = stock_quantity + ? WHERE product_id = ?", (qty, pid))
            
            # 3. 退款給買家
            cursor.execute("UPDATE User SET wallet_balance = wallet_balance + ? WHERE user_id = ?", (total_amount, buyer_id))
            
            # 4. 更新訂單狀態
            cursor.execute('UPDATE "Order" SET status = ?, cancellation_reason = ? WHERE order_id = ?', 
                           ('CANCELLED', final_reason, order_id))
            
            conn.commit()
            QMessageBox.information(self, "成功", "訂單已成功取消，款項已全額退還給買家，並恢復庫存！")
            self.load_seller_orders()
            
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"取消訂單發生嚴重錯誤: {e}")
        finally:
            conn.close()

    def on_tab_changed(self, index):
        """當子頁籤切換時重新載入對應資料"""
        if index == 0:
            self.load_my_products()
        elif index == 1:
            self.load_seller_orders()
