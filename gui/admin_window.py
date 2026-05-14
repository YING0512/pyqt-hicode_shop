from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLineEdit, 
                             QPushButton, QLabel, QHBoxLayout, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget, QComboBox)
from PyQt5.QtCore import Qt
from db_cloud import get_connection

class AdminWindow(QWidget):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.setWindowTitle("HiCode Shop - 管理員後台")
        self.resize(700, 500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        title = QLabel("⚙️ 管理員後台系統")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #8e44ad; margin-bottom: 10px;")
        layout.addWidget(title)

        self.tabs = QTabWidget()
        
        # 1. 兌換碼管理頁籤
        self.tab_codes = QWidget()
        self.init_codes_tab()
        self.tabs.addTab(self.tab_codes, "🎟️ 兌換碼管理")
        
        # 2. 會員管理頁籤
        self.tab_users = QWidget()
        self.init_users_tab()
        self.tabs.addTab(self.tab_users, "👥 會員管理")
        
        self.tabs.currentChanged.connect(self.on_tab_changed)
        layout.addWidget(self.tabs)
        
        self.setLayout(layout)
        self.load_codes()

    def on_tab_changed(self, index):
        if index == 0:
            self.load_codes()
        elif index == 1:
            self.load_users()

    def init_codes_tab(self):
        layout = QVBoxLayout(self.tab_codes)
        
        # 新增代碼區塊
        form_layout = QFormLayout()
        self.input_code = QLineEdit()
        self.input_code.setPlaceholderText("例如: VIP888")
        form_layout.addRow("🎟️ 兌換代碼:", self.input_code)
        
        self.input_value = QLineEdit()
        self.input_value.setPlaceholderText("例如: 1000")
        form_layout.addRow("💰 面額:", self.input_value)
        
        self.input_max_uses = QLineEdit()
        self.input_max_uses.setText("1")
        form_layout.addRow("👥 限制人數:", self.input_max_uses)
        layout.addLayout(form_layout)
        
        btn_add = QPushButton("發行兌換碼")
        btn_add.setStyleSheet("background-color: #2ecc71; color: white; padding: 8px; font-weight: bold;")
        btn_add.clicked.connect(self.create_code)
        layout.addWidget(btn_add)
        
        # 代碼列表
        self.table_codes = QTableWidget()
        self.table_codes.setColumnCount(4)
        self.table_codes.setHorizontalHeaderLabels(["代碼", "面額", "已使用/上限", "操作"])
        self.table_codes.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table_codes)

    def load_codes(self):
        conn = get_connection()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT code_id, code, value, max_uses, current_uses FROM RedemptionCode ORDER BY created_at DESC")
            codes = cursor.fetchall()
            
            self.table_codes.setRowCount(len(codes))
            for row_idx, rc in enumerate(codes):
                c_id, code, value, max_uses, current_uses = rc
                
                self.table_codes.setItem(row_idx, 0, QTableWidgetItem(code))
                self.table_codes.setItem(row_idx, 1, QTableWidgetItem(f"${float(value):.2f}"))
                self.table_codes.setItem(row_idx, 2, QTableWidgetItem(f"{current_uses} / {max_uses}"))
                
                btn_del = QPushButton("刪除")
                btn_del.setStyleSheet("background-color: #e74c3c; color: white; border-radius: 3px;")
                btn_del.clicked.connect(lambda checked, cid=c_id: self.delete_code(cid))
                self.table_codes.setCellWidget(row_idx, 3, btn_del)
                
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"載入兌換碼失敗: {e}")
        finally:
            conn.close()

    def create_code(self):
        code = self.input_code.text().strip()
        value_str = self.input_value.text().strip()
        max_uses_str = self.input_max_uses.text().strip()
        
        if not code or not value_str or not max_uses_str:
            QMessageBox.warning(self, "錯誤", "請填寫完整資訊！")
            return
            
        try:
            value = float(value_str)
            max_uses = int(max_uses_str)
        except ValueError:
            QMessageBox.warning(self, "錯誤", "面額與人數必須為數字！")
            return
            
        conn = get_connection()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO RedemptionCode (code, value, max_uses) VALUES (?, ?, ?)", (code, value, max_uses))
            conn.commit()
            QMessageBox.information(self, "成功", f"成功發行兌換碼: {code}")
            self.input_code.clear()
            self.input_value.clear()
            self.input_max_uses.setText("1")
            self.load_codes()
        except Exception as e:
            if 'UNIQUE' in str(e).upper():
                QMessageBox.warning(self, "錯誤", "此兌換碼已經存在了！")
            else:
                QMessageBox.critical(self, "錯誤", f"發行失敗: {e}")
        finally:
            conn.close()

    def delete_code(self, code_id):
        reply = QMessageBox.question(self, '確認刪除', '確定要刪除這組兌換碼嗎？', 
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes: return
        
        conn = get_connection()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM RedemptionCode WHERE code_id = ?", (code_id,))
            conn.commit()
            self.load_codes()
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"刪除失敗: {e}")
        finally:
            conn.close()

    def init_users_tab(self):
        layout = QVBoxLayout(self.tab_users)
        
        header_layout = QHBoxLayout()
        lbl = QLabel("全站會員列表")
        lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(lbl)
        
        btn_refresh = QPushButton("🔄 重新整理")
        btn_refresh.clicked.connect(self.load_users)
        header_layout.addWidget(btn_refresh, alignment=Qt.AlignRight)
        layout.addLayout(header_layout)

        self.table_users = QTableWidget()
        self.table_users.setColumnCount(5)
        self.table_users.setHorizontalHeaderLabels(["ID", "帳號", "餘額", "權限", "操作"])
        self.table_users.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table_users)

    def load_users(self):
        conn = get_connection()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, username, wallet_balance, role FROM User ORDER BY user_id ASC")
            users = cursor.fetchall()
            
            self.table_users.setRowCount(len(users))
            for row_idx, user in enumerate(users):
                u_id, username, balance, role = user
                if balance is None: balance = 0.0
                
                self.table_users.setItem(row_idx, 0, QTableWidgetItem(str(u_id)))
                self.table_users.setItem(row_idx, 1, QTableWidgetItem(username))
                self.table_users.setItem(row_idx, 2, QTableWidgetItem(f"${float(balance):.2f}"))
                
                # 權限下拉選單
                combo_role = QComboBox()
                combo_role.addItems(['user', 'seller', 'admin'])
                combo_role.setCurrentText(role)
                self.table_users.setCellWidget(row_idx, 3, combo_role)
                
                # 儲存按鈕
                btn_save = QPushButton("儲存變更")
                btn_save.setStyleSheet("background-color: #3498db; color: white; border-radius: 3px;")
                btn_save.clicked.connect(lambda checked, uid=u_id, combo=combo_role: self.update_user_role(uid, combo.currentText()))
                self.table_users.setCellWidget(row_idx, 4, btn_save)
                
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"載入會員失敗: {e}")
        finally:
            conn.close()

    def update_user_role(self, user_id, new_role):
        conn = get_connection()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE User SET role = ? WHERE user_id = ?", (new_role, user_id))
            conn.commit()
            QMessageBox.information(self, "成功", f"成功將會員 #{user_id} 權限更新為 {new_role}！")
            self.load_users()
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"更新權限失敗: {e}")
        finally:
            conn.close()
