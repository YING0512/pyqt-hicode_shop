from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QLabel, QMessageBox
from PyQt5.QtCore import pyqtSignal, Qt
from db_cloud import get_connection, hash_password

class LoginWindow(QWidget):
    """
    登入與註冊視窗類別
    負責處理使用者的身分驗證，並在成功登入後發送訊號通知主程式。
    """
    # 定義一個自訂訊號，當登入成功時觸發，並傳遞 (user_id, username, role) 三個參數給主程式
    login_successful = pyqtSignal(int, str, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("HiCode Shop - 登入")
        self.resize(350, 250)
        self.init_ui()

    def init_ui(self):
        """初始化登入介面的排版與元件"""
        layout = QVBoxLayout()

        # 標題標籤
        title = QLabel("HiCode Shop 雲端商城")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 15px;")
        layout.addWidget(title)

        # 表單佈局，用於整齊排列標籤與輸入框
        form_layout = QFormLayout()
        
        # 帳號輸入框
        self.input_username = QLineEdit()
        self.input_username.setPlaceholderText("請輸入帳號 (或 Email)")
        form_layout.addRow("帳號:", self.input_username)
        
        # 密碼輸入框
        self.input_password = QLineEdit()
        self.input_password.setPlaceholderText("請輸入密碼")
        # 設定密碼框為隱藏模式 (顯示為星號或圓點)
        self.input_password.setEchoMode(QLineEdit.Password)
        form_layout.addRow("密碼:", self.input_password)
        
        layout.addLayout(form_layout)

        # 登入按鈕
        self.btn_login = QPushButton("登入")
        self.btn_login.setStyleSheet("background-color: #3498db; color: white; padding: 8px;")
        self.btn_login.clicked.connect(self.handle_login)
        layout.addWidget(self.btn_login)

        # 註冊按鈕
        self.btn_register = QPushButton("註冊新帳號")
        self.btn_register.setStyleSheet("background-color: #2ecc71; color: white; padding: 8px;")
        self.btn_register.clicked.connect(self.handle_register)
        layout.addWidget(self.btn_register)

        self.setLayout(layout)

    def handle_login(self):
        """處理登入邏輯：驗證帳號密碼，並獲取使用者權限"""
        username = self.input_username.text().strip()
        password = self.input_password.text().strip()

        # 簡單防呆：確保欄位不為空
        if not username or not password:
            QMessageBox.warning(self, "錯誤", "請輸入帳號與密碼！")
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "錯誤", "無法連接至雲端資料庫！")
            return

        try:
            cursor = conn.cursor()
            # 密碼在傳輸比對前，必須先轉換為相同的雜湊值
            hashed_pw = hash_password(password)
            
            # 從 User 資料表查詢帳號與雜湊密碼是否吻合
            cursor.execute("SELECT user_id, username, role FROM User WHERE (username = ? OR email = ?) AND password_hash = ?", 
                           (username, username, hashed_pw))
            user = cursor.fetchone()

            if user:
                # 登入成功
                user_id, uname, role = user
                QMessageBox.information(self, "成功", f"登入成功！歡迎 {uname}")
                # 觸發訊號，通知主程式開啟主視窗，並傳遞使用者資訊
                self.login_successful.emit(user_id, uname, role)
            else:
                # 登入失敗
                QMessageBox.warning(self, "失敗", "帳號或密碼錯誤！")
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"登入發生錯誤: {e}")
        finally:
            conn.close()

    def handle_register(self):
        """處理註冊邏輯：建立新使用者帳號"""
        username = self.input_username.text().strip()
        password = self.input_password.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "錯誤", "請輸入要註冊的帳號與密碼！")
            return

        conn = get_connection()
        if not conn: return

        try:
            cursor = conn.cursor()
            hashed_pw = hash_password(password)
            
            # 新註冊的帳號，Email 暫時使用帳號名稱作為替代 (實務上應分開)
            cursor.execute("INSERT INTO User (username, email, password_hash) VALUES (?, ?, ?)", 
                           (username, username, hashed_pw))
            conn.commit()
        finally:
            conn.close()
