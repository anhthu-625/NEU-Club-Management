from flask import request, jsonify, session
from datetime import datetime


def register_api(app, db, User, Student, Club, Event, Product, CartItem, Order, OrderItem):
    def current_user():
        user_id = session.get('user_id')
        if not user_id:
            return None
        return User.query.get(user_id)

    def require_student(user):
        if not user or not user.is_student():
            return None
        return user

    @app.route('/api/auth/register', methods=['POST'])
    def api_register():
        data = request.get_json() or {}
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        user_type = data.get('user_type', '')
        if not username or not email or not password or not user_type:
            return jsonify({'error': 'Vui lòng điền đầy đủ thông tin'}), 400
        if not email.endswith('@neu.edu.vn'):
            return jsonify({'error': 'Email phải có đuôi @neu.edu.vn'}), 400
        if len(password) < 6:
            return jsonify({'error': 'Mật khẩu phải có ít nhất 6 ký tự'}), 400
        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            return jsonify({'error': 'Tên đăng nhập hoặc email đã tồn tại'}), 400
        user = User(username=username, email=email, user_type=user_type, status='active')
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        if user_type == 'student':
            student_code = data.get('student_code', '').strip() or username
            full_name = data.get('full_name', '').strip() or username
            student = Student(user_id=user.id, student_code=student_code, full_name=full_name)
            db.session.add(student)
        elif user_type == 'club':
            club_name = data.get('club_name', '').strip() or username
            field = data.get('field', '').strip() or 'CLB'
            club = Club(user_id=user.id, club_name=club_name, field=field, description=data.get('description', ''), status='approved')
            db.session.add(club)
        db.session.commit()
        return jsonify({'message': 'Đăng ký thành công'}), 201

    @app.route('/api/auth/login', methods=['POST'])
    def api_login():
        data = request.get_json() or {}
        username = data.get('username', '').strip()
        password = data.get('password', '')
        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            return jsonify({'error': 'Đăng nhập không chính xác'}), 401
        session.clear()
        session['user_id'] = user.id
        return jsonify({'message': 'Đăng nhập thành công', 'user': user.to_dict()}), 200

    @app.route('/api/auth/logout', methods=['POST'])
    def api_logout():
        session.clear()
        return jsonify({'message': 'Đăng xuất thành công'}), 200

    @app.route('/api/auth/user', methods=['GET'])
    def api_user():
        user = current_user()
        if not user:
            return jsonify({'user': None}), 200
        student = None
        if user.is_student() and user.student_profile:
            student = user.student_profile.to_dict()
        return jsonify({'user': user.to_dict(), 'student': student}), 200

    @app.route('/api/clubs', methods=['GET'])
    def api_clubs():
        clubs = Club.query.filter_by(status='approved').all()
        return jsonify({'clubs': [club.to_dict() for club in clubs]}), 200

    @app.route('/api/events', methods=['GET'])
    def api_events():
        events = Event.query.all()
        return jsonify({'events': [event.to_dict() for event in events]}), 200

    @app.route('/api/products', methods=['GET'])
    def api_products():
        products = Product.query.all()
        return jsonify({'products': [product.to_dict() for product in products]}), 200

    @app.route('/api/cart', methods=['GET'])
    def api_cart():
        user = current_user()
        student = require_student(user)
        if not student:
            return jsonify({'error': 'Chỉ sinh viên mới được phép'}), 403
        items = CartItem.query.filter_by(student_id=student.id).all()
        return jsonify({'items': [item.to_dict() for item in items], 'total': sum(item.product.price * item.quantity for item in items)}), 200

    @app.route('/api/cart/add', methods=['POST'])
    def api_cart_add():
        user = current_user()
        student = require_student(user)
        if not student:
            return jsonify({'error': 'Chỉ sinh viên mới được phép'}), 403
        data = request.get_json() or {}
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))
        product = Product.query.get(product_id)
        if not product or product.quantity < quantity:
            return jsonify({'error': 'Sản phẩm không khả dụng'}), 400
        cart_item = CartItem.query.filter_by(student_id=student.id, product_id=product.id).first()
        if cart_item:
            cart_item.quantity += quantity
        else:
            cart_item = CartItem(student_id=student.id, product_id=product.id, quantity=quantity)
            db.session.add(cart_item)
        db.session.commit()
        return jsonify({'message': 'Đã thêm vào giỏ hàng'}), 200

    @app.route('/api/cart/remove', methods=['POST'])
    def api_cart_remove():
        user = current_user()
        student = require_student(user)
        if not student:
            return jsonify({'error': 'Chỉ sinh viên mới được phép'}), 403
        data = request.get_json() or {}
        product_id = data.get('product_id')
        cart_item = CartItem.query.filter_by(student_id=student.id, product_id=product_id).first()
        if not cart_item:
            return jsonify({'error': 'Sản phẩm không tồn tại trong giỏ hàng'}), 404
        db.session.delete(cart_item)
        db.session.commit()
        return jsonify({'message': 'Đã xóa khỏi giỏ hàng'}), 200

    @app.route('/api/orders', methods=['GET'])
    def api_orders():
        user = current_user()
        student = require_student(user)
        if not student:
            return jsonify({'error': 'Chỉ sinh viên mới được phép'}), 403
        orders = Order.query.filter_by(student_id=student.id).all()
        return jsonify({'orders': [order.to_dict() for order in orders]}), 200

    @app.route('/api/orders/checkout', methods=['POST'])
    def api_checkout():
        user = current_user()
        student = require_student(user)
        if not student:
            return jsonify({'error': 'Chỉ sinh viên mới được phép'}), 403
        cart_items = CartItem.query.filter_by(student_id=student.id).all()
        if not cart_items:
            return jsonify({'error': 'Giỏ hàng trống'}), 400
        order = Order(student_id=student.id, total_price=sum(item.product.price * item.quantity for item in cart_items), status='pending')
        db.session.add(order)
        db.session.flush()
        for item in cart_items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price_per_unit=item.product.price
            )
            item.product.quantity -= item.quantity
            db.session.add(order_item)
            db.session.delete(item)
        db.session.commit()
        return jsonify({'message': 'Thanh toán thành công', 'order': order.to_dict()}), 201

    return app
