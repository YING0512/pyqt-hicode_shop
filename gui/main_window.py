from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QTabWidget, QHBoxLayout, QPushButton
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, pyqtSignal

# 匯入我們新建立的各個頁籤模組
from gui.tab_products import TabProducts
from gui.tab_cart import TabCart
from gui.tab_orders import TabOrders
from gui.tab_wallet import TabWallet
from gui.tab_seller import TabSeller

class MainWindow(QMainWindow):
    """
    商城主視窗類別
    作為整個應用程式的核心框架，負責裝載各個功能頁籤 (Tabs)，並提供最高層級的導航。
    """
    logout_requested = pyqtSignal()
    def __init__(self, user_id, username, role):
        super().__init__()
        # 儲存登入使用者的基本資訊，這些資訊將會傳遞給子頁籤使用
        self.user_id = user_id
        self.username = username
        self.role = role
        
        # 設定視窗標題與初始大小
        self.setWindowTitle(f"HiCode Shop - 商城首頁 (會員: {self.username})")
        self.resize(800, 600)
        self.init_ui()

    def init_ui(self):
        """初始化主視窗介面，建立頁籤系統"""
        # QMainWindow 需要一個中央 Widget 作為所有內容的容器
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 使用垂直佈局來排列上方的標題列與下方的頁籤列
        layout = QVBoxLayout(central_widget)

        # 1. 頂部標題列 (包含歡迎詞與可能的管理員按鈕)
        header_layout = QHBoxLayout()
        welcome_label = QLabel(f"歡迎回來，{self.username}！開始您的購物之旅吧。")
        welcome_label.setFont(QFont("Arial", 16, QFont.Bold))
        welcome_label.setStyleSheet("color: #2c3e50; padding: 10px;")
        header_layout.addWidget(welcome_label)

        # 權限控管：如果登入者的身分是管理員，則在右上角顯示「管理員後台」按鈕
        if self.role == 'admin':
            self.btn_admin = QPushButton("⚙️ 管理員後台")
            self.btn_admin.setStyleSheet("background-color: #8e44ad; color: white; padding: 8px; font-weight: bold; border-radius: 4px;")
            self.btn_admin.clicked.connect(self.open_admin_panel)
            header_layout.addWidget(self.btn_admin, alignment=Qt.AlignRight)

        # 新增登出按鈕
        self.btn_logout = QPushButton("🚪 登出")
        self.btn_logout.setStyleSheet("background-color: #e74c3c; color: white; padding: 8px; font-weight: bold; border-radius: 4px; margin-left: 10px;")
        self.btn_logout.clicked.connect(self.logout_requested.emit)
        header_layout.addWidget(self.btn_logout, alignment=Qt.AlignRight)

        layout.addLayout(header_layout)

        # 2. 建立頁籤系統 (QTabWidget)
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("font-size: 14px;")
        
        # --- 加入各個功能頁籤 ---
        
        # 1. 商品商城：讓買家瀏覽所有上架的商品並加入購物車
        self.tab_products = TabProducts(self.user_id)
        self.tabs.addTab(self.tab_products, "🛍️ 商品商城")
        
        # 2. 購物車：管理欲購買的商品、調整數量與結帳
        self.tab_cart = TabCart(self.user_id)
        self.tabs.addTab(self.tab_cart, "🛒 我的購物車")
        
        # 3. 訂單紀錄：查看歷史消費清單與明細
        self.tab_orders = TabOrders(self.user_id)
        self.tabs.addTab(self.tab_orders, "📦 訂單紀錄")
        
        # 4. 會員錢包：查看儲值金餘額與兌換代碼
        self.tab_wallet = TabWallet(self.user_id)
        self.tabs.addTab(self.tab_wallet, "💰 會員錢包")

        # 5. 賣家中心 (權限控管)：僅限賣家或管理員才能看到此頁籤
        if self.role in ['seller', 'admin']:
            self.tab_seller = TabSeller(self.user_id)
            self.tabs.addTab(self.tab_seller, "🏪 賣家中心")

        # 綁定頁籤切換事件，用於動態重新載入該頁籤的最新資料
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        layout.addWidget(self.tabs)

    def on_tab_changed(self, index):
        """
        當使用者切換頁籤時觸發的事件處理函式。
        藉由判斷被選取的頁籤索引 (index)，呼叫對應模組的資料載入函式，
        確保使用者每次切換過去看到的都是最新的雲端資料庫狀態。
        """
        if index == 0:
            self.tab_products.load_products()
        elif index == 1:
            self.tab_cart.load_cart()
        elif index == 2:
            self.tab_orders.load_orders()
        elif index == 3:
            self.tab_wallet.load_balance()
        elif index == 4 and hasattr(self, 'tab_seller'):
            self.tab_seller.load_my_products()

    def open_admin_panel(self):
        """
        開啟獨立的管理員後台子視窗。
        此視窗不屬於頁籤系統，而是作為一個獨立的彈出視窗處理進階功能 (如全站會員管理、發行兌換碼)。
        """
        # 為了避免循環匯入 (Circular Import)，我們在函式內部才匯入 AdminWindow 模組
        from gui.admin_window import AdminWindow
        self.admin_window = AdminWindow(self.user_id)
        self.admin_window.show()
