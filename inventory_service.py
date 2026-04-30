from flask import Flask, request, jsonify
from flask_cors import CORS

from sqlalchemy import create_engine, Column, Integer, String, DECIMAL
from sqlalchemy.orm import declarative_base, sessionmaker
import os

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.environ.get("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    echo=False
)

Base = declarative_base()
Session = sessionmaker(bind=engine)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_code = Column(String(20), unique=True, nullable=False)
    product_name = Column(String(100), nullable=False)
    brand = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    stock = Column(Integer, nullable=False)
    price = Column(DECIMAL(10, 2), nullable=False)


Base.metadata.create_all(engine)


@app.route("/inventory", methods=["GET"])
def get_inventory():
    session = Session()

    products = session.query(Product).all()

    result = []

    for product in products:
        result.append({
            "product_code": product.product_code,
            "product_name": product.product_name,
            "brand": product.brand,
            "category": product.category,
            "stock": product.stock,
            "price": float(product.price)
        })

    session.close()

    return jsonify({
        "status": "success",
        "inventory": result
    })


@app.route("/update_inventory", methods=["POST"])
def update_inventory():
    data = request.get_json()

    product_code = data.get("product_code")
    quantity = int(data.get("quantity", 0))

    if not product_code or quantity <= 0:
        return jsonify({
            "status": "failed",
            "message": "Product code and valid quantity are required"
        }), 400

    session = Session()

    product = session.query(Product).filter_by(
        product_code=product_code
    ).first()

    if product is None:
        session.close()
        return jsonify({
            "status": "failed",
            "message": "Product code not found"
        }), 404

    if product.stock < quantity:
        available_stock = product.stock
        session.close()
        return jsonify({
            "status": "failed",
            "message": f"Insufficient stock. Available: {available_stock} units"
        }), 400

    product.stock -= quantity
    session.commit()

    response = {
        "status": "success",
        "remaining_stock": product.stock,
        "product_code": product.product_code,
        "product_name": product.product_name,
        "brand": product.brand,
        "category": product.category,
        "price": float(product.price)
    }

    session.close()

    return jsonify(response)


if __name__ == "__main__":
    app.run(port=5001, debug=True)
