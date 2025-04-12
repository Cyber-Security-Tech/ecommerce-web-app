from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from . import db, login_manager
from .models import User, Product, CartItem, Order
from .forms import RegisterForm, LoginForm, ProductForm, CheckoutForm
import stripe
from config import Config

main_bp = Blueprint('main_bp', __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@main_bp.route("/")
def index():
    products = Product.query.all()
    return render_template("index.html", products=products)

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
    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product.id).first()
    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = CartItem(user_id=current_user.id, product_id=product.id, quantity=1)
        db.session.add(cart_item)
    db.session.commit()
    flash(f"Added {product.name} to cart.")
    return redirect(url_for('main_bp.index'))

@main_bp.route("/cart", methods=["GET"])
@login_required
def cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(item.product.price * item.quantity for item in cart_items)
    form = CheckoutForm()
    return render_template("cart.html", cart_items=cart_items, total=total, form=form)

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

# ✅ Stripe Checkout Session version
@main_bp.route("/checkout", methods=["POST"])
@login_required
def checkout():
    form = CheckoutForm()
    if form.validate_on_submit():
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        if not cart_items:
            flash("Your cart is empty.")
            return redirect(url_for("main_bp.cart"))

        total_amount = int(sum(item.product.price * item.quantity for item in cart_items) * 100)
        stripe.api_key = Config.STRIPE_SECRET_KEY

        try:
            line_items = [{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': item.product.name,
                    },
                    'unit_amount': int(item.product.price * 100),
                },
                'quantity': item.quantity,
            } for item in cart_items]

            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                mode='payment',
                success_url=url_for('main_bp.checkout_success', _external=True),
                cancel_url=url_for('main_bp.cart', _external=True),
            )

            return redirect(session.url, code=303)

        except Exception as e:
            flash("Payment failed.")
            return redirect(url_for("main_bp.cart"))
    else:
        flash("Invalid form submission.")
        return redirect(url_for("main_bp.cart"))

# ✅ Handles Stripe redirect after success
@main_bp.route("/checkout/success")
@login_required
def checkout_success():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total_amount = sum(item.product.price * item.quantity for item in cart_items)
    order = Order(user_id=current_user.id, total_amount=total_amount)
    db.session.add(order)
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
            category=form.category.data
        )
        db.session.add(new_product)
        db.session.commit()
        flash("Product added.")
        return redirect(url_for("main_bp.admin"))

    products = Product.query.all()
    return render_template("admin.html", form=form, products=products)
