from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLineEdit, 
                             QPushButton, QLabel, QMessageBox, QHBoxLayout)
from PyQt5.QtCore import Qt
from db_cloud import get_connection

class TabWallet(QWidget):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # 顯示餘額
        self.lbl_balance = QLabel("當前餘額: $0.00")
        self.lbl_balance.setStyleSheet("font-size: 24px; font-weight: bold; color: #f39c12; margin-top: 20px; margin-bottom: 20px;")
        self.lbl_balance.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_balance)

        # 儲值區域 (僅保留兌換碼)
        form_layout = QFormLayout()

        self.input_code = QLineEdit()
        self.input_code.setPlaceholderText("請輸入系統管理員發放的兌換碼")
        form_layout.addRow("🎁 兌換碼:", self.input_code)
        
        layout.addLayout(form_layout)

        # 按鈕區塊
        btn_layout = QHBoxLayout()

        btn_redeem = QPushButton("兌換代碼")
        btn_redeem.setStyleSheet("background-color: #9b59b6; color: white; padding: 10px; font-size: 14px; border-radius: 5px;")
        btn_redeem.clicked.connect(self.redeem_code)
        btn_layout.addWidget(btn_redeem)

        layout.addLayout(btn_layout)

        layout.addStretch()
        self.setLayout(layout)

    def load_balance(self):
        conn = get_connection()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT wallet_balance FROM User WHERE user_id = ?", (self.user_id,))
            res = cursor.fetchone()
            if res:
                balance = res[0]
                if balance is None: balance = 0.0
                self.lbl_balance.setText(f"當前餘額: ${float(balance):.2f}")
        except Exception as e:
            print("載入餘額失敗:", e)
        finally:
            conn.close()

    def redeem_code(self):
        code = self.input_code.text().strip()
        if not code:
            QMessageBox.warning(self, "錯誤", "請輸入兌換碼！")
            return

        conn = get_connection()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            
            # 1. 檢查代碼是否存在
            cursor.execute("SELECT code_id, value, max_uses, current_uses FROM RedemptionCode WHERE code = ?", (code,))
            rc = cursor.fetchone()
            
            if not rc:
                QMessageBox.warning(self, "無效代碼", "您輸入的兌換碼無效！")
                return
                
            code_id, value, max_uses, current_uses = rc
            
            # 2. 檢查使用上限
            if int(current_uses) >= int(max_uses):
                QMessageBox.warning(self, "兌換失敗", "此兌換碼已被領取完畢 (達到使用上限)！")
                return
                
            # 3. 檢查是否已領取過
            cursor.execute("SELECT history_id FROM RedemptionHistory WHERE code_id = ? AND user_id = ?", (code_id, self.user_id))
            if cursor.fetchone():
                QMessageBox.warning(self, "兌換失敗", "您已經領取過此兌換碼，每人限領一次！")
                return
                
            # 4. 執行兌換：更新次數、寫入歷史、增加餘額
            cursor.execute("UPDATE RedemptionCode SET current_uses = current_uses + 1 WHERE code_id = ?", (code_id,))
            cursor.execute("INSERT INTO RedemptionHistory (code_id, user_id) VALUES (?, ?)", (code_id, self.user_id))
            cursor.execute("UPDATE User SET wallet_balance = wallet_balance + ? WHERE user_id = ?", (value, self.user_id))
            
            conn.commit()
            QMessageBox.information(self, "兌換成功", f"恭喜！您已成功兌換 ${float(value):.2f}！")
            self.input_code.clear()
            self.load_balance()
            
        except Exception as e:
            QMessageBox.critical(self, "兌換失敗", f"發生錯誤: {e}")
        finally:
            conn.close()
