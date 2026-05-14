import sys
from PyQt5.QtWidgets import QApplication
from gui.login_window import LoginWindow
from gui.main_window import MainWindow
from db_cloud import ensure_schema_updated

class ShopApp:
    """
    主應用程式類別
    負責初始化 PyQt5 應用程式、管理登入視窗與主視窗之間的切換流程。
    """
    def __init__(self):
        # 建立 PyQt5 應用程式實例
        self.app = QApplication(sys.argv)
        
        # 初始化登入視窗，此時尚未顯示
        self.login_window = LoginWindow()
        self.main_window = None
        
        # 將登入視窗的「login_successful」訊號綁定到 show_main_window 方法
        # 當使用者成功登入時，登入視窗會發射此訊號並傳遞使用者資訊
        self.login_window.login_successful.connect(self.show_main_window)
        
    def run(self):
        """
        啟動應用程式的方法。
        """
        # 程式啟動時，首先顯示登入畫面
        self.login_window.show()
        # 進入應用程式的主迴圈 (Event Loop)，並在關閉時安全退出
        sys.exit(self.app.exec_())

    def show_main_window(self, user_id, username, role):
        """
        處理登入成功的邏輯。
        
        參數:
            user_id (int): 登入使用者的資料庫 ID
            username (str): 登入使用者的帳號名稱
            role (str): 登入使用者的權限角色 (例如: 'user', 'seller', 'admin')
        """
        # 關閉登入視窗
        self.login_window.close()
        
        # 實例化主商城視窗，並傳入使用者的相關資訊
        self.main_window = MainWindow(user_id, username, role)
        
        # 綁定登出訊號
        self.main_window.logout_requested.connect(self.handle_logout)
        
        # 顯示主商城視窗
        self.main_window.show()

    def handle_logout(self):
        """處理登出邏輯"""
        if self.main_window:
            self.main_window.close()
            self.main_window = None
            
        # 重新實例化登入視窗以清空舊資料
        self.login_window = LoginWindow()
        self.login_window.login_successful.connect(self.show_main_window)
        self.login_window.show()

if __name__ == "__main__":
    # 1. 啟動前先檢查雲端資料庫的結構是否完整 (例如是否具備 seller_id, role 等後期擴充的欄位)
    print("正在檢查資料庫結構...")
    ensure_schema_updated()
    
    # 2. 結構檢查完畢後，正式啟動圖形介面程式
    print("正在啟動 HiCode Shop PyQt5 視窗程式...")
    shop_app = ShopApp()
    shop_app.run()
