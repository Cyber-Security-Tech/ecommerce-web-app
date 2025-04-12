from app import create_app, db
from app.models import Product

app = create_app()

with app.app_context():
    print("Trying to query Product table:")
    print(Product.query.all())  # will return [] if database is empty, or raise error if broken
