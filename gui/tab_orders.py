from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLabel, QHBoxLayout, QMessageBox, QHeaderView, QInputDialog)
from PyQt5.QtCore import Qt
from db_cloud import get_connection

class TabOrders(QWidget):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        header_layout = QHBoxLayout()
        title = QLabel("📦 我的訂單紀錄")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(title)
        
        btn_refresh = QPushButton("🔄 重新整理")
        btn_refresh.clicked.connect(self.load_orders)
        header_layout.addWidget(btn_refresh, alignment=Qt.AlignRight)
        layout.addLayout(header_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["訂單編號", "日期", "總金額", "狀態", "操作/備註"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)

        self.setLayout(layout)

    def load_orders(self):
        conn = get_connection()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT order_id, order_date, total_amount, status, cancellation_reason, rejection_reason FROM "Order" WHERE user_id = ? ORDER BY order_id DESC', (self.user_id,))
            orders = cursor.fetchall()
            
            self.table.setRowCount(len(orders))
            
            # 定義狀態中文化與顏色
            status_map = {
                'PENDING': ('待處理', Qt.black),
                'COMPLETED': ('已完成', Qt.darkGreen),
                'CANCELLED': ('已取消', Qt.red)
            }
            
            for row_idx, order in enumerate(orders):
                o_id, date, amount, status, reason, rej_reason = order
                self.table.setItem(row_idx, 0, QTableWidgetItem(f"#{o_id}"))
                self.table.setItem(row_idx, 1, QTableWidgetItem(str(date)))
                self.table.setItem(row_idx, 2, QTableWidgetItem(f"${float(amount):.2f}"))
                
                # 顯示中文化狀態
                if status == 'PENDING' and reason:
                    status_text = '取消申請中'
                    color = Qt.darkYellow
                else:
                    status_text, color = status_map.get(status, (status, Qt.black))
                    
                status_item = QTableWidgetItem(status_text)
                status_item.setForeground(color)
                self.table.setItem(row_idx, 3, status_item)
                
                # 處理第五欄的「操作」或「備註」
                if status == 'PENDING' and not reason:
                    # 允許申請取消
                    action_widget = QWidget()
                    action_layout = QVBoxLayout(action_widget)
                    action_layout.setContentsMargins(5, 4, 5, 4)
                    action_layout.setAlignment(Qt.AlignCenter)
                    
                    # 若曾被駁回，顯示駁回緣由
                    if rej_reason:
                        lbl_rej = QLabel(f"駁回緣由: {rej_reason}")
                        lbl_rej.setStyleSheet("color: #e74c3c; font-size: 12px;")
                        action_layout.addWidget(lbl_rej)
                        
                    btn_cancel = QPushButton("申請取消")
                    btn_cancel.setStyleSheet("background-color: #e74c3c; color: white; border-radius: 4px; padding: 6px 12px; font-weight: bold;")
                    btn_cancel.clicked.connect(lambda checked, oid=o_id: self.request_cancel(oid))
                    
                    action_layout.addWidget(btn_cancel)
                    self.table.setCellWidget(row_idx, 4, action_widget)
                elif status == 'PENDING' and reason:
                    # 取消申請中
                    self.table.setItem(row_idx, 4, QTableWidgetItem(f"原因: {reason}"))
                elif status == 'CANCELLED':
                    # 已取消訂單不顯示按鈕，只顯示備註
                    reason_text = f"原因: {reason}" if reason else "已取消"
                    self.table.setItem(row_idx, 4, QTableWidgetItem(reason_text))
                else:
                    self.table.setItem(row_idx, 4, QTableWidgetItem(""))
                    
            self.table.resizeRowsToContents()
        except Exception as e:
            QMessageBox.critical(self, "載入失敗", f"無法載入訂單: {e}")
        finally:
            conn.close()

    def request_cancel(self, order_id):
        """買家提出取消訂單申請"""
        # 彈出輸入對話框，要求填寫理由
        reason, ok = QInputDialog.getText(self, "申請取消訂單", f"請輸入訂單 #{order_id} 的取消理由:")
        if not ok:
            return  # 使用者按下了取消
            
        reason = reason.strip()
        if not reason:
            QMessageBox.warning(self, "錯誤", "必須填寫取消理由才能送出申請！")
            return
            
        conn = get_connection()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            # 由於資料庫有 status 的 Check Constraint，我們不修改 status，僅寫入 reason，並以此作為判斷依據
            # 如果原本有駁回理由，在此次申請時將其清空，以便重新審核
            cursor.execute('UPDATE "Order" SET cancellation_reason = ?, rejection_reason = NULL WHERE order_id = ? AND user_id = ?',
                           (reason, order_id, self.user_id))
            conn.commit()
            QMessageBox.information(self, "成功", "取消申請已送出，請等待賣家同意。")
            self.load_orders()
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"送出取消申請失敗: {e}")
        finally:
            conn.close()
