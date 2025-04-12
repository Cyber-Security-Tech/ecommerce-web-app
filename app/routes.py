from flask import Blueprint, render_template, redirect, url_for, flash, request, g
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from . import db, login_manager
from .models import User, Product, CartItem, Order, OrderItem
from .forms import RegisterForm, LoginForm, ProductForm, CheckoutForm, QuantityForm
import stripe
from config import Config

main_bp = Blueprint('main_bp', __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@main_bp.before_app_request
def load_cart_count():
    if current_user.is_authenticated:
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        g.cart_count = sum(item.quantity for item in cart_items)
    else:
        g.cart_count = 0

@main_bp.route("/")
def index():
    search_query = request.args.get("search", "")
    selected_category = request.args.get("category", "")
    sort_option = request.args.get("sort", "")

    products_query = Product.query

    if search_query:
        products_query = products_query.filter(Product.name.ilike(f"%{search_query}%"))

    if selected_category:
        products_query = products_query.filter(Product.category.ilike(f"%{selected_category}%"))

    if sort_option == "price_asc":
        products_query = products_query.order_by(Product.price.asc())
    elif sort_option == "price_desc":
        products_query = products_query.order_by(Product.price.desc())
    elif sort_option == "name_asc":
        products_query = products_query.order_by(Product.name.asc())
    elif sort_option == "name_desc":
        products_query = products_query.order_by(Product.name.desc())

    products = products_query.all()
    categories = [c[0] for c in db.session.query(Product.category).distinct() if c[0]]

    return render_template("index.html", products=products, categories=categories, search_query=search_query, selected_category=selected_category, sort_option=sort_option)

@main_bp.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash("Email already registered.")
            return redirect(url_for('main_bp.register'))
        hashed_password = generate_password_hash(form.password.data)
        user = User(email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful. Please log in.")
        return redirect(url_for('main_bp.login'))
    return render_template("register.html", form=form)

@main_bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            flash("Logged in successfully.")
            return redirect(url_for('main_bp.index'))
        flash("Invalid email or password.")
    return render_template("login.html", form=form)

@main_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.")
    return redirect(url_for('main_bp.index'))

@main_bp.route("/product/<int:product_id>")
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template("product.html", product=product)

@main_bp.route("/add_to_cart/<int:product_id>")
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    if product.stock <= 0:
        flash("This product is out of stock.")
        return redirect(url_for("main_bp.product_detail", product_id=product.id))

    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product.id).first()
    if cart_item:
        if cart_item.quantity < product.stock:
            cart_item.quantity += 1
        else:
            flash("Reached available stock limit.")
            return redirect(url_for("main_bp.cart"))
    else:
        cart_item = CartItem(user_id=current_user.id, product_id=product.id, quantity=1)
        db.session.add(cart_item)
    db.session.commit()
    flash(f"Added {product.name} to cart.")
    return redirect(url_for('main_bp.product_detail', product_id=product.id))

@main_bp.route("/cart", methods=["GET", "POST"])
@login_required
def cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(item.product.price * item.quantity for item in cart_items)
    form = CheckoutForm()
    quantity_forms = {item.id: QuantityForm(obj=item) for item in cart_items}
    return render_template("cart.html", cart_items=cart_items, total=total, form=form, quantity_forms=quantity_forms)

@main_bp.route("/update_cart/<int:item_id>", methods=["POST"])
@login_required
def update_cart(item_id):
    item = CartItem.query.get_or_404(item_id)
    form = QuantityForm()
    if item.user_id != current_user.id:
        flash("Unauthorized.")
        return redirect(url_for("main_bp.cart"))

    if form.validate_on_submit():
        quantity = form.quantity.data
        if quantity > item.product.stock:
            flash("Not enough stock available.")
        else:
            item.quantity = quantity
            db.session.commit()
            flash("Quantity updated.")
    return redirect(url_for("main_bp.cart"))

@main_bp.route("/remove_from_cart/<int:item_id>")
@login_required
def remove_from_cart(item_id):
    item = CartItem.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        flash("Unauthorized.")
        return redirect(url_for("main_bp.cart"))
    db.session.delete(item)
    db.session.commit()
    flash("Item removed.")
    return redirect(url_for("main_bp.cart"))

@main_bp.route("/checkout", methods=["POST"])
@login_required
def checkout():
    form = CheckoutForm()
    if form.validate_on_submit():
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        if not cart_items:
            flash("Your cart is empty.")
            return redirect(url_for("main_bp.cart"))

        for item in cart_items:
            if item.quantity > item.product.stock:
                flash(f"Not enough stock for {item.product.name}.")
                return redirect(url_for("main_bp.cart"))

        stripe.api_key = Config.STRIPE_SECRET_KEY

        line_items = [{
            'price_data': {
                'currency': 'usd',
                'product_data': {'name': item.product.name},
                'unit_amount': int(item.product.price * 100),
            },
            'quantity': item.quantity,
        } for item in cart_items]

        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                mode='payment',
                success_url=url_for('main_bp.checkout_success', _external=True),
                cancel_url=url_for('main_bp.cart', _external=True),
            )
            return redirect(session.url, code=303)
        except Exception:
            flash("Payment failed.")
            return redirect(url_for("main_bp.cart"))

    flash("Invalid form submission.")
    return redirect(url_for("main_bp.cart"))

@main_bp.route("/checkout/success")
@login_required
def checkout_success():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total_amount = sum(item.product.price * item.quantity for item in cart_items)

    order = Order(user_id=current_user.id, total_amount=total_amount)
    db.session.add(order)
    db.session.commit()

    for item in cart_items:
        order_item = OrderItem(order_id=order.id, product_id=item.product.id, quantity=item.quantity)
        item.product.stock -= item.quantity
        db.session.add(order_item)

    CartItem.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash("Payment successful! Thank you for your purchase.")
    return redirect(url_for("main_bp.index"))

@main_bp.route("/admin", methods=["GET", "POST"])
@login_required
def admin():
    if not current_user.is_admin:
        flash("Admins only.")
        return redirect(url_for("main_bp.index"))

    form = ProductForm()
    if form.validate_on_submit():
        new_product = Product(
            name=form.name.data,
            description=form.description.data,
            price=form.price.data,
            image_url=form.image_url.data,
            category=form.category.data,
            stock=form.stock.data
        )
        db.session.add(new_product)
        db.session.commit()
        flash("Product added.")
        return redirect(url_for("main_bp.admin"))

    products = Product.query.all()
    return render_template("admin.html", form=form, products=products)

@main_bp.route("/admin/edit/<int:product_id>", methods=["GET", "POST"])
@login_required
def edit_product(product_id):
    if not current_user.is_admin:
        flash("Admins only.")
        return redirect(url_for("main_bp.index"))

    product = Product.query.get_or_404(product_id)
    form = ProductForm(obj=product)

    if form.validate_on_submit():
        product.name = form.name.data
        product.description = form.description.data
        product.price = form.price.data
        product.image_url = form.image_url.data
        product.category = form.category.data
        product.stock = form.stock.data
        db.session.commit()
        flash("Product updated.")
        return redirect(url_for("main_bp.admin"))

    return render_template("edit_product.html", form=form, product=product)

@main_bp.route("/admin/delete/<int:product_id>")
@login_required
def delete_product(product_id):
    if not current_user.is_admin:
        flash("Admins only.")
        return redirect(url_for("main_bp.index"))

    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash("Product deleted.")
    return redirect(url_for("main_bp.admin"))

@main_bp.route("/orders")
@login_required
def orders():
    user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.timestamp.desc()).all()
    return render_template("orders.html", orders=user_orders)
