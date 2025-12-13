import os  # 引入 os 套件讀取環境變數

from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
# 引入驗證相關套件
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
# 引入 abort 用來顯示錯誤
from flask import abort


app = Flask(__name__)
app.config['SECRET_KEY'] = 'YourSecretKey'  # 務必設定 Secret Key 才能使用 Session

# --- 資料庫連線設定 ---
dbname = "Final_Project_Booking_Hotel_System"
user = "postgres"
password = "1017"
host = "localhost"

# --- 資料庫連線設定 ---
def get_db_connection():
    # 嘗試從環境變數取得雲端資料庫網址
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        # 如果有雲端網址 (代表在 Render/Heroku 上)，直接使用
        # 注意：有些平台網址開頭是 postgres://，psycopg2 需要 postgresql://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        conn = psycopg2.connect(database_url)
    else:
        # 如果沒有 (代表在本機)，使用原本的設定
        conn = psycopg2.connect(
            dbname="Final_Project_Booking_Hotel_System",
            user="postgres",
            password="1017",
            host="localhost"
        )
    return conn

# 設定 Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # 如果未登入者嘗試進入受保護頁面，導向 login

# User 類別 (繼承 UserMixin 以獲得 is_authenticated 等屬性)
class User(UserMixin):
    def __init__(self, id, email, name, role, phone=None): 
        self.id = id
        self.email = email
        self.name = name
        self.role = role
        self.phone = phone  # 儲存電話

# 這是 Flask-Login 用來載入使用者的方式
@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, email, name, role, phone FROM "Users" WHERE id = %s', (user_id,))
    user_data = cur.fetchone()
    cur.close()
    conn.close()
    if user_data:
        return User(id=user_data[0], email=user_data[1], name=user_data[2], role=user_data[3], phone=user_data[4])
    return None

# --- 1. 首頁與瀏覽服務 (Frontend: Browse Services) ---
# 對應作業要求：User-friendly interface to browse and book various services
@app.route('/')
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 從資料庫抓取所有 'Services' (房型) 資訊供使用者瀏覽
    # 您需要在資料庫先建立 Services 表格並塞入資料
    cur.execute('SELECT * FROM "Services"')
    services = cur.fetchall()
    
    cur.close()
    conn.close()
    
    # 渲染 index.html，並將 services 傳遞過去顯示
    return render_template('index.html', services=services)

# --- 註冊功能 ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        phone = request.form.get('phone')  #接收電話
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 檢查 Email 是否重複
        cur.execute('SELECT id FROM "Users" WHERE email = %s', (email,))
        if cur.fetchone():
            flash('Email already exists.')
            return redirect(url_for('register'))
        
        # 加密密碼並存入資料庫
        hashed_password = generate_password_hash(password)
        cur.execute('INSERT INTO "Users" (email, name, password_hash, role, phone) VALUES (%s, %s, %s, %s, %s)', (email, name, hashed_password, 'user', phone))
        conn.commit()
        cur.close()
        conn.close()
        
        return redirect(url_for('login'))
    
    return render_template('register.html')

# --- 登入功能 ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT id, email, password_hash, name, role, phone FROM "Users" WHERE email = %s', (email,))
        user_data = cur.fetchone()
        cur.close()
        conn.close()
        
        # 驗證密碼 (檢查雜湊值)
        # 必須先檢查 user_data 是否為 None (即帳號是否存在)
        # 只有在 user_data 存在的情況下，才去檢查密碼 (check_password_hash)
        if user_data and check_password_hash(user_data[2], password):
            # 登入成功：建立 User 物件
            user = User(id=user_data[0], email=user_data[1], name=user_data[3], role=user_data[4], phone=user_data[5])
            login_user(user)
            return redirect(url_for('index'))
        else:
            # 登入失敗 (帳號不存在 或 密碼錯誤)
            flash('Login failed. Please check your email and password.')
            
    return render_template('login.html')

# --- 登出功能 ---
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# --- 2. 預約/訂房功能 (Frontend: Booking Form) ---
# 對應作業要求：Booking form with customizable options
# 這裡設計讓使用者點擊某個服務後，進入填寫資料頁面
@app.route('/book/<int:service_id>', methods=['GET', 'POST'])
# @login_required  <-- 如果你希望只有登入才能預約，可以把這行的註解拿掉
def book_service(service_id):
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        # 1. 接收基本資料
        booker_name = request.form['booker_name']
        booker_phone = request.form['booker_phone']
        booker_email = request.form['booker_email']
        check_in_date = request.form['check_in_date']
        check_out_date = request.form['check_out_date']
        
        # 2. 接收客製化選項 (Customizable Options)
        adults = request.form.get('adults', '1')
        children = request.form.get('children', '0')
        
        # 接收勾選的多個加購項目 (使用 getlist)
        adults = request.form.get('adults', '1')
        children = request.form.get('children', '0')
        addons = request.form.getlist('addons') 
        addons_str = ", ".join(addons) if addons else "None"
        special_requests = request.form.get('special_requests', '')

        # 3. 將這些客製化資訊整合成一個字串，存入 'details' 欄位
        # 格式範例： "Guests: 2 Adults, 0 Children | Add-ons: Breakfast | Note: Late check-in"
        formatted_details = f"Guests: {adults} Adults, {children} Children | Add-ons: {addons_str} | Note: {special_requests}"

        # 4. 抓取房型名稱
        cur.execute('SELECT service_name FROM "Services" WHERE service_id = %s', (service_id,))
        service_row = cur.fetchone()
        service_name = service_row[0] if service_row else "Unknown Service"
        if service_row:
            service_name = service_row[0]
        else:
            service_name = "Unknown Service"

        # 5. 寫入資料庫
        sql = """
            INSERT INTO "BookOrder" 
            (booker_name, booker_phone, booker_email, check_in_date, check_out_date, booked_rooms, details)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING book_id
        """
        cur.execute(sql, (booker_name, booker_phone, booker_email, check_in_date, check_out_date, service_name, formatted_details))

        # 取得新產生的 ID
        new_book_id = cur.fetchone()[0]

        conn.commit()
        
        cur.close()
        conn.close()

        # 加入成功訊息，並重導向到該筆訂單的詳細頁面
        flash('Booking Successful! Thank you for your reservation.')
        return redirect(url_for('booking_details', id=new_book_id))
    
    else:
        # GET 請求：顯示表單
        cur.execute('SELECT * FROM "Services" WHERE service_id = %s', (service_id,))
        service = cur.fetchone()
        cur.close()
        conn.close()
        return render_template('booking_form.html', service=service)

# --- 3. 使用者查詢訂單狀態 (Frontend: Check Status) ---
@app.route('/search', methods=['POST'])
def search_booking():
    booking_id = request.form.get('booking_id')
    result = None
    
    # 簡單驗證輸入是否為數字
    if not booking_id or not booking_id.strip().isdigit():
        # 如果輸入錯誤，重新導回首頁並顯示錯誤 (這裡假設 index 有處理 services)
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM "Services"')
        services = cur.fetchall()
        cur.close()
        conn.close()
        return render_template('index.html', services=services, error_message="Invalid Input: ID must be numeric.")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 查詢該 ID 的訂單
    cur.execute('SELECT booked_rooms, check_in_date, check_out_date FROM "BookOrder" WHERE book_id = %s', (booking_id,))
    result = cur.fetchone()
    
    # 為了在搜尋後也能顯示服務列表，這裡也要抓取 Services
    cur.execute('SELECT * FROM "Services"')
    services = cur.fetchall()
    
    cur.close()
    conn.close()
    
    if result:
        return render_template('index.html', services=services, search_result=result, booking_id=booking_id)
    else:
        return render_template('index.html', services=services, error_message="Booking not found")

# --- 會員查看自己的訂單 ---
@app.route('/my_bookings')
@login_required  # 必須登入才能看
def my_bookings():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 根據登入者的 email 篩選訂單，並按 ID 倒序排列 (最新的在上面)
    cur.execute('SELECT * FROM "BookOrder" WHERE booker_email = %s ORDER BY book_id DESC', (current_user.email,))
    my_orders = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('my_bookings.html', bookings=my_orders)

# --- 4. 訂單詳細頁面 ---
@app.route('/details/<int:id>')
def booking_details(id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    sql = """
        SELECT book_date, book_id, check_in_date, check_out_date, 
               booker_name, booker_phone, booker_email, details, booked_rooms
        FROM "BookOrder" 
        WHERE book_id = %s
    """
    cur.execute(sql, (id,))
    booking = cur.fetchone()
    
    cur.close()
    conn.close()
    
    if booking:
        return render_template('details.html', booking=booking)
    else:
        return "Booking not found", 404

# --- 5. 管理員儀表板 (Admin Dashboard) ---
# 對應作業要求：Manage bookings with search, filter...
@app.route('/admin', methods=['GET', 'POST'])
@login_required  # 必須先登入
def admin():
    # 檢查是否為 admin，如果不是就踢出去 (顯示 403 禁止訪問)
    if current_user.role != 'admin':
        return "Access Denied: You are not an administrator.", 403

    results = []
    conn = get_db_connection()
    cur = conn.cursor()
    
    if request.method == 'POST':
        # --- 搜尋功能 ---
        search_query = request.form.get('search_query')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        # 使用 1=1 技巧動態串接 SQL
        sql = """
            SELECT book_id, booked_rooms, booker_name, booker_email, check_in_date, check_out_date 
            FROM "BookOrder" 
            WHERE 1=1
        """
        params = []

        if search_query:
            sql += " AND (booker_name ILIKE %s OR CAST(book_id AS TEXT) LIKE %s)"
            params.append(f"%{search_query}%")
            params.append(f"%{search_query}%")

        if start_date and end_date:
            sql += " AND check_in_date BETWEEN %s AND %s"
            params.append(start_date)
            params.append(end_date)

        # 加上排序，讓最新的訂單在上面
        sql += " ORDER BY book_id DESC"
        
        cur.execute(sql, tuple(params))
        results = cur.fetchall()
    else:
        # GET 請求：預設顯示所有訂單
        cur.execute('SELECT book_id, booked_rooms, booker_name, booker_email, check_in_date, check_out_date FROM "BookOrder" ORDER BY book_id DESC')
        results = cur.fetchall()

    cur.close()
    conn.close()
    return render_template('admin.html', results=results)

# --- 6. 管理員修改訂單 (Admin: Modify) ---
@app.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
@login_required  # 必須登入
def edit_booking(id):
    # 檢查權限
    if current_user.role != 'admin':
        return "Access Denied", 403

    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        # 接收修改後的資料並更新資料庫
        new_name = request.form.get('booker_name')
        new_phone = request.form.get('booker_phone')
        new_email = request.form.get('booker_email')
        new_checkin = request.form.get('check_in_date')
        new_checkout = request.form.get('check_out_date')
        
        sql = """
            UPDATE "BookOrder" 
            SET booker_name = %s, booker_phone = %s, booker_email = %s, 
                check_in_date = %s, check_out_date = %s
            WHERE book_id = %s
        """
        cur.execute(sql, (new_name, new_phone, new_email, new_checkin, new_checkout, id))
        conn.commit()
        
        cur.close()
        conn.close()
        return redirect(url_for('admin'))
    
    else:
        # GET 請求：撈出舊資料填入編輯表單
        # [關鍵修正] 這裡不能用 SELECT *，必須指定欄位順序以配合 HTML template 的索引
        # HTML 預期的順序: [1]=id, [2]=check_in, [3]=check_out, [4]=name, [5]=phone, [6]=email
        sql = """
            SELECT book_date, book_id, check_in_date, check_out_date, 
                   booker_name, booker_phone, booker_email 
            FROM "BookOrder" 
            WHERE book_id = %s
        """
        cur.execute(sql, (id,))
        booking = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if booking:
            return render_template('edit_booking.html', booking=booking)
        else:
            return "Booking not found", 404

# --- 7. 管理員取消訂單 (Admin: Cancel) ---
# 對應作業要求：Manage bookings with ... cancel options
@app.route('/admin/delete/<int:id>', methods=['POST'])
def delete_booking(id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # [新增功能] 刪除指定 ID 的訂單
    cur.execute('DELETE FROM "BookOrder" WHERE book_id = %s', (id,))
    conn.commit()
    
    cur.close()
    conn.close()
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)