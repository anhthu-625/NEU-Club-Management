from flask import Flask, render_template, session, g, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
db_path = os.path.join(app.root_path, 'db', 'club_management.db')
os.makedirs(os.path.dirname(db_path), exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

USER_TYPE_STUDENT = 'student'
USER_TYPE_CLUB = 'club'
USER_TYPE_ADMIN = 'admin'
STATUS_ACTIVE = 'active'
STATUS_APPROVED = 'approved'
STATUS_PENDING = 'pending'

class AnonymousUser:
    is_authenticated = False

    def is_student(self):
        return False

    def is_club(self):
        return False

    def is_admin(self):
        return False

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default=STATUS_ACTIVE)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    student_profile = db.relationship('Student', uselist=False, backref='user', cascade='all, delete-orphan')
    club_profile = db.relationship('Club', uselist=False, backref='user', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_student(self):
        return self.user_type == USER_TYPE_STUDENT

    def is_club(self):
        return self.user_type == USER_TYPE_CLUB

    def is_admin(self):
        return self.user_type == USER_TYPE_ADMIN

    @property
    def is_authenticated(self):
        return True

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'user_type': self.user_type,
            'status': self.status
        }

class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    student_code = db.Column(db.String(50), unique=True, nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    major = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    cart_items = db.relationship('CartItem', backref='student', cascade='all, delete-orphan')
    orders = db.relationship('Order', backref='student', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'student_code': self.student_code,
            'full_name': self.full_name,
            'major': self.major,
        }

class Club(db.Model):
    __tablename__ = 'clubs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    club_name = db.Column(db.String(200), nullable=False, unique=True)
    field = db.Column(db.String(100))
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default=STATUS_APPROVED)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    events = db.relationship('Event', backref='club', cascade='all, delete-orphan')
    products = db.relationship('Product', backref='club', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'club_name': self.club_name,
            'field': self.field,
            'description': self.description,
            'status': self.status,
        }

class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey('clubs.id'), nullable=False)
    event_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(255))
    start_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'event_name': self.event_name,
            'description': self.description,
            'location': self.location,
            'start_date': self.start_date.isoformat(),
            'club_name': self.club.club_name if self.club else None,
        }

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey('clubs.id'), nullable=False)
    product_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False, default=0.0)
    quantity = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'product_name': self.product_name,
            'description': self.description,
            'price': self.price,
            'quantity': self.quantity,
            'club_name': self.club.club_name if self.club else None,
        }

class CartItem(db.Model):
    __tablename__ = 'cart_items'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product')

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product_name': self.product.product_name,
            'price': self.product.price,
            'quantity': self.quantity,
            'subtotal': self.product.price * self.quantity,
            'club_name': self.product.club.club_name if self.product.club else None,
        }

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    total_price = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship('OrderItem', backref='order', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'total_price': self.total_price,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'items': [item.to_dict() for item in self.items],
        }

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    price_per_unit = db.Column(db.Float, nullable=False)

    product = db.relationship('Product')

    def to_dict(self):
        return {
            'product_name': self.product.product_name,
            'quantity': self.quantity,
            'price_per_unit': self.price_per_unit,
            'subtotal': self.quantity * self.price_per_unit,
        }

@app.before_request
def load_current_user():
    g.user = None
    user_id = session.get('user_id')
    if user_id:
        g.user = User.query.get(user_id)

@app.context_processor
def inject_user():
    current_user = g.user if g.user is not None else AnonymousUser()
    unread_count = 0
    return {'current_user': current_user, 'unread_count': unread_count}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'], endpoint='login')
def login_page():
    if g.user:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            flash('Tên đăng nhập hoặc mật khẩu không chính xác', 'danger')
            return render_template('login.html')
        session.clear()
        session['user_id'] = user.id
        if user.is_student():
            return redirect(url_for('student_dashboard'))
        if user.is_club():
            return redirect(url_for('club_dashboard'))
        if user.is_admin():
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('index'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'], endpoint='register')
def register_page():
    if g.user:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        student_code = request.form.get('student_code', '').strip()
        full_name = request.form.get('full_name', '').strip()

        if not username or not email or not password or not student_code or not full_name:
            flash('Vui lòng điền đầy đủ thông tin', 'danger')
            return render_template('register.html')
        if not email.endswith('@neu.edu.vn'):
            flash('Email phải có đuôi @neu.edu.vn', 'danger')
            return render_template('register.html')
        if len(password) < 6:
            flash('Mật khẩu phải có ít nhất 6 ký tự', 'danger')
            return render_template('register.html')
        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            flash('Tên đăng nhập hoặc email đã tồn tại', 'danger')
            return render_template('register.html')

        user = User(username=username, email=email, user_type=USER_TYPE_STUDENT, status=STATUS_ACTIVE)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        student = Student(user_id=user.id, student_code=student_code, full_name=full_name)
        db.session.add(student)
        db.session.commit()

        flash('Đăng ký thành công. Vui lòng đăng nhập.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/clubs', endpoint='clubs')
def clubs_page():
    return render_template('clubs.html')

@app.route('/events', endpoint='events')
def events_page():
    return render_template('events.html')

@app.route('/products', endpoint='products_list')
def products_list_page():
    products = Product.query.all()
    clubs = Club.query.all()
    return render_template('products.html', products=products, clubs=clubs)

@app.route('/cart', endpoint='cart')
def cart_page():
    if not g.user or not g.user.is_student():
        return redirect(url_for('login'))
    student = g.user.student_profile
    cart_items = student.cart_items if student else []
    return render_template('cart.html', cart_items=cart_items)

@app.route('/orders', endpoint='orders')
def orders_page():
    if not g.user or not g.user.is_student():
        return redirect(url_for('login'))
    student = g.user.student_profile
    orders = student.orders if student else []
    return render_template('orders.html', orders=orders)

@app.route('/orders_list', endpoint='orders_list')
def orders_list_page():
    if not g.user or not g.user.is_student():
        return redirect(url_for('login'))
    student = g.user.student_profile
    orders = student.orders if student else []
    return render_template('orders.html', orders=orders)

@app.route('/notifications', endpoint='notifications_list')
def notifications_list():
    return render_template('notifications.html', notifications=[])

@app.route('/change-credentials', methods=['GET', 'POST'], endpoint='change_credentials')
def change_credentials():
    if not g.user:
        return redirect(url_for('login'))
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        if password and password == confirm:
            g.user.set_password(password)
            db.session.commit()
            flash('Mật khẩu đã được cập nhật.', 'success')
        else:
            flash('Mật khẩu không khớp hoặc thiếu.', 'danger')
    return render_template('change_credentials.html')

@app.route('/student/dashboard', endpoint='student_dashboard')
def student_dashboard():
    if not g.user or not g.user.is_student():
        return redirect(url_for('login'))
    clubs = Club.query.limit(4).all()
    return render_template('student/dashboard.html',
                           unread_notifications=0,
                           club_count=0,
                           event_count=0,
                           order_count=0,
                           club_posts=[],
                           my_clubs=[],
                           upcoming_events=[],
                           clubs=clubs)

@app.route('/student/profile', endpoint='student_profile')
def student_profile():
    if not g.user or not g.user.is_student():
        return redirect(url_for('login'))
    return render_template('student/profile.html', student=g.user.student_profile)

@app.route('/student/profile/edit', endpoint='student_profile_edit')
def student_profile_edit():
    if not g.user or not g.user.is_student():
        return redirect(url_for('login'))
    return render_template('student/profile_edit.html', student=g.user.student_profile)

@app.route('/student/activities', endpoint='student_activities')
def student_activities():
    if not g.user or not g.user.is_student():
        return redirect(url_for('login'))
    return render_template('student/activities.html', activities=[])

@app.route('/student/clubs', endpoint='student_clubs')
def student_clubs():
    if not g.user or not g.user.is_student():
        return redirect(url_for('login'))
    clubs = Club.query.all()
    return render_template('student/clubs.html', clubs=clubs)

@app.route('/student/events', endpoint='student_events')
def student_events():
    events = Event.query.all()
    return render_template('student/events.html', events=events)

@app.route('/student/club-register', methods=['GET', 'POST'], endpoint='student_club_register')
def student_club_register():
    if not g.user or not g.user.is_student():
        return redirect(url_for('login'))
    return render_template('student/club_register.html')

@app.route('/club/dashboard', endpoint='club_dashboard')
def club_dashboard():
    if not g.user or not g.user.is_club():
        return redirect(url_for('login'))
    club = g.user.club_profile
    if club is not None:
        club.members = getattr(club, 'members', [])
        club.applications = getattr(club, 'applications', [])
    return render_template('club/dashboard.html', club=club)

@app.route('/club/profile', endpoint='club_profile')
def club_profile():
    if not g.user or not g.user.is_club():
        return redirect(url_for('login'))
    return render_template('club/profile.html', club=g.user.club_profile)

@app.route('/club/profile/edit', methods=['GET', 'POST'], endpoint='club_profile_edit')
def club_profile_edit():
    if not g.user or not g.user.is_club():
        return redirect(url_for('login'))
    club = g.user.club_profile
    return render_template('club/profile_edit.html', club=club)

@app.route('/club/products', endpoint='club_products')
def club_products():
    if not g.user or not g.user.is_club():
        return redirect(url_for('login'))
    products = g.user.club_profile.products if g.user.club_profile else []
    return render_template('club/products.html', products=products)

@app.route('/club/posts', endpoint='club_posts')
def club_posts():
    if not g.user or not g.user.is_club():
        return redirect(url_for('login'))
    return render_template('club/posts.html', posts=[])

@app.route('/club/orders', endpoint='club_orders')
def club_orders():
    if not g.user or not g.user.is_club():
        return redirect(url_for('login'))
    return render_template('club/orders.html', orders=[])

@app.route('/club/events', endpoint='club_events')
def club_events():
    if not g.user or not g.user.is_club():
        return redirect(url_for('login'))
    return render_template('club/events.html', events=[])

@app.route('/club/applications', endpoint='club_applications')
def club_applications():
    if not g.user or not g.user.is_club():
        return redirect(url_for('login'))
    return render_template('club/applications.html', applications=[])

@app.route('/club/reports', endpoint='club_reports')
def club_reports():
    if not g.user or not g.user.is_club():
        return redirect(url_for('login'))
    return render_template('club/reports.html')

@app.route('/club/members', endpoint='club_members')
def club_members():
    if not g.user or not g.user.is_club():
        return redirect(url_for('login'))
    return render_template('club/members.html', members=[])

@app.route('/admin/dashboard', endpoint='admin_dashboard')
def admin_dashboard():
    if not g.user or not g.user.is_admin():
        return redirect(url_for('login'))
    return render_template('admin/dashboard.html')

@app.route('/admin/events', endpoint='admin_events')
def admin_events():
    if not g.user or not g.user.is_admin():
        return redirect(url_for('login'))
    return render_template('admin/events.html', events=Event.query.all())

@app.route('/admin/products', endpoint='admin_products')
def admin_products():
    if not g.user or not g.user.is_admin():
        return redirect(url_for('login'))
    return render_template('admin/products.html', products=Product.query.all())

@app.route('/admin/clubs', endpoint='admin_clubs')
def admin_clubs():
    if not g.user or not g.user.is_admin():
        return redirect(url_for('login'))
    return render_template('admin/clubs.html', clubs=Club.query.all())

@app.route('/admin/reports', endpoint='admin_reports')
def admin_reports():
    if not g.user or not g.user.is_admin():
        return redirect(url_for('login'))
    return render_template('admin/reports.html')

@app.route('/clubs/<int:club_id>', endpoint='club_detail')
def club_detail(club_id):
    club = Club.query.get_or_404(club_id)
    events = club.events if club else []
    products = club.products if club else []
    return render_template('club_detail.html', club=club, events=events, products=products)

@app.route('/products/<int:product_id>', endpoint='product_detail')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product_detail.html', product=product)

@app.route('/events/<int:event_id>', endpoint='event_detail')
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    return render_template('event_detail.html', event=event)

@app.route('/cart/checkout', methods=['POST'], endpoint='checkout_cart')
def checkout_cart():
    if not g.user or not g.user.is_student():
        return redirect(url_for('login'))
    flash('Chức năng thanh toán đang được cập nhật.', 'info')
    return redirect(url_for('cart'))

@app.route('/products/<int:product_id>/add', methods=['POST'], endpoint='add_to_cart')
def add_to_cart(product_id):
    if not g.user or not g.user.is_student():
        return redirect(url_for('login'))
    flash('Sản phẩm đã được thêm vào giỏ hàng.', 'success')
    return redirect(url_for('cart'))

@app.route('/notifications/read-all', methods=['POST'], endpoint='read_all_notifications')
def read_all_notifications():
    flash('Tất cả thông báo đã được đánh dấu là đã đọc.', 'success')
    return redirect(url_for('notifications_list'))

@app.route('/student/clubs/<int:club_id>/apply', methods=['POST'], endpoint='student_apply_club')
def student_apply_club(club_id):
    if not g.user or not g.user.is_student():
        return redirect(url_for('login'))
    flash('Đã gửi yêu cầu gia nhập CLB.', 'success')
    return redirect(url_for('student_clubs'))

@app.route('/club/create-event', methods=['GET', 'POST'], endpoint='create_event')
def create_event():
    if not g.user or not g.user.is_club():
        return redirect(url_for('login'))
    return render_template('club/create_event.html')

@app.route('/club/create-product', methods=['GET', 'POST'], endpoint='create_product')
def create_product():
    if not g.user or not g.user.is_club():
        return redirect(url_for('login'))
    return render_template('club/create_product.html')

@app.route('/club/create-post', methods=['GET', 'POST'], endpoint='create_post')
def create_post():
    if not g.user or not g.user.is_club():
        return redirect(url_for('login'))
    return render_template('club/create_post.html')

@app.route('/club/events/<int:event_id>/delete', methods=['POST'], endpoint='delete_event')
def delete_event(event_id):
    flash('Sự kiện đã được xóa.', 'success')
    return redirect(url_for('club_events'))

@app.route('/club/posts/<int:post_id>/delete', methods=['POST'], endpoint='delete_post')
def delete_post(post_id):
    flash('Bài viết đã được xóa.', 'success')
    return redirect(url_for('club_posts'))

@app.route('/club/products/<int:product_id>/delete', methods=['POST'], endpoint='delete_product')
def delete_product(product_id):
    flash('Sản phẩm đã được xóa.', 'success')
    return redirect(url_for('club_products'))

@app.route('/club/events/<int:event_id>/edit', methods=['GET', 'POST'], endpoint='edit_event')
def edit_event(event_id):
    return render_template('club/edit_event.html', event=Event.query.get(event_id))

@app.route('/club/posts/<int:post_id>/edit', methods=['GET', 'POST'], endpoint='edit_post')
def edit_post(post_id):
    return render_template('club/edit_post.html', post=None)

@app.route('/club/products/<int:product_id>/edit', methods=['GET', 'POST'], endpoint='edit_product')
def edit_product(product_id):
    return render_template('club/edit_product.html', product=Product.query.get(product_id))

@app.route('/events/<int:event_id>/check-in', methods=['POST'], endpoint='event_check_in')
def event_check_in(event_id):
    flash('Điểm danh đã được cập nhật.', 'success')
    return redirect(url_for('event_detail', event_id=event_id))

@app.route('/events/<int:event_id>/check-out', methods=['POST'], endpoint='event_check_out')
def event_check_out(event_id):
    flash('Đã rời khỏi sự kiện.', 'success')
    return redirect(url_for('event_detail', event_id=event_id))

@app.route('/club/events/<int:event_id>/registrations', endpoint='event_registrations')
def event_registrations(event_id):
    return render_template('club/event_registrations.html', registrations=[])

@app.route('/events/<int:event_id>/token/<action>', endpoint='get_cico_token')
def get_cico_token(event_id, action):
    return {'token': 'placeholder'}

@app.route('/club/applications/<int:app_id>/<action>', methods=['POST'], endpoint='process_application')
def process_application(app_id, action):
    flash('Yêu cầu đã được xử lý.', 'success')
    return redirect(url_for('club_applications'))

@app.route('/club/event-registrations/<int:reg_id>/<action>', methods=['POST'], endpoint='process_event_registration')
def process_event_registration(reg_id, action):
    flash('Đăng ký sự kiện đã được cập nhật.', 'success')
    return redirect(url_for('event_registrations', event_id=0))

@app.route('/events/<int:event_id>/register', methods=['POST'], endpoint='register_event')
def register_event(event_id):
    flash('Bạn đã đăng ký tham gia sự kiện.', 'success')
    return redirect(url_for('event_detail', event_id=event_id))

@app.route('/cart/remove/<int:product_id>', methods=['POST'], endpoint='remove_from_cart')
def remove_from_cart(product_id):
    flash('Đã xoá sản phẩm khỏi giỏ hàng.', 'success')
    return redirect(url_for('cart'))

@app.route('/club/members/<int:member_id>/remove', methods=['POST'], endpoint='remove_member')
def remove_member(member_id):
    flash('Thành viên đã được loại khỏi CLB.', 'success')
    return redirect(url_for('club_members'))

@app.route('/cart/update/<int:product_id>/<action>', methods=['POST'], endpoint='update_cart')
def update_cart(product_id, action):
    flash('Số lượng giỏ hàng đã được cập nhật.', 'success')
    return redirect(url_for('cart'))

@app.route('/club/orders/<int:order_id>/<action>', methods=['POST'], endpoint='update_order_status')
def update_order_status(order_id, action):
    flash('Trạng thái đơn hàng đã được cập nhật.', 'success')
    return redirect(url_for('club_orders'))

@app.route('/events/<int:event_id>/verify-token/<action>', methods=['POST'], endpoint='verify_cico_token')
def verify_cico_token(event_id, action):
    return {'success': True}

@app.route('/logout', endpoint='logout')
def logout_page():
    session.clear()
    return redirect(url_for('index'))

from api import register_api
register_api(app, db, User, Student, Club, Event, Product, CartItem, Order, OrderItem)


def create_default_data():
    db.create_all()
    if not User.query.filter_by(user_type=USER_TYPE_ADMIN).first():
        admin = User(username='admin', email='admin@neu.edu.vn', user_type=USER_TYPE_ADMIN, status=STATUS_ACTIVE)
        admin.set_password('admin123')
        db.session.add(admin)

    if not Club.query.first():
        club1 = User(username='musicclub', email='musicclub@neu.edu.vn', user_type=USER_TYPE_CLUB, status=STATUS_ACTIVE)
        club1.set_password('club1234')
        club_profile = Club(user=club1, club_name='NEU Music Club', field='Âm nhạc', description='CLB âm nhạc cho sinh viên yêu nhạc.', status=STATUS_APPROVED)
        db.session.add(club1)
        db.session.add(club_profile)

        club2 = User(username='sportclub', email='sportclub@neu.edu.vn', user_type=USER_TYPE_CLUB, status=STATUS_ACTIVE)
        club2.set_password('club1234')
        club_profile2 = Club(user=club2, club_name='NEU Sports Club', field='Thể thao', description='CLB thể thao với các hoạt động năng động.', status=STATUS_APPROVED)
        db.session.add(club2)
        db.session.add(club_profile2)

        event1 = Event(club=club_profile, event_name='Concert NEU', description='Buổi biểu diễn âm nhạc đặc sắc cho sinh viên.', location='Hội trường A', start_date=datetime.utcnow())
        event2 = Event(club=club_profile2, event_name='Giải Bóng Rổ', description='Giải đấu bóng rổ cho sinh viên.', location='Sân vận động', start_date=datetime.utcnow())
        db.session.add_all([event1, event2])

        product1 = Product(club=club_profile, product_name='Áo phông Music Club', description='Áo phông chính thức của CLB âm nhạc.', price=150000, quantity=20)
        product2 = Product(club=club_profile2, product_name='Mũ thể thao', description='Mũ thời trang dành cho thành viên CLB thể thao.', price=120000, quantity=15)
        db.session.add_all([product1, product2])

    db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        create_default_data()
    app.run(debug=True, host='0.0.0.0', port=5000)
