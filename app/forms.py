from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, FloatField, IntegerField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, URL

class RegisterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Register")

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember Me")
    submit = SubmitField("Login")

class ProductForm(FlaskForm):
    name = StringField("Product Name", validators=[DataRequired()])
    description = TextAreaField("Description")
    price = FloatField("Price", validators=[DataRequired(), NumberRange(min=0)])
    image_url = StringField("Image URL", validators=[URL()])
    category = StringField("Category")
    stock = IntegerField("Stock", validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField("Save Product")

class QuantityForm(FlaskForm):
    quantity = IntegerField("Quantity", validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField("Update")

class CheckoutForm(FlaskForm):
    submit = SubmitField("Proceed to Checkout")
