from flask import Flask, request, jsonify
from flask_cors import CORS

import os
import random
from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, DECIMAL, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker


app = Flask(__name__)
CORS(app)


# =========================================================
# DATABASE CONNECTION
# =========================================================

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is missing")

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True
)

Base = declarative_base()
Session = sessionmaker(bind=engine)


# =========================================================
# ORM MODELS
# =========================================================

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_code = Column(String(20), unique=True, nullable=False)
    product_name = Column(String(100), nullable=False)
    brand = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    stock = Column(Integer, nullable=False)
    price = Column(DECIMAL(10, 2), nullable=False)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String(30), unique=True, nullable=False)
    order_timestamp = Column(DateTime, nullable=False)
    customer_name = Column(String(100), nullable=False)
    product_code = Column(String(20), nullable=False)
    product_name = Column(String(100), nullable=False)
    brand = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    quantity = Column(Integer, nullable=False)
    price_per_unit = Column(DECIMAL(10, 2), nullable=False)
    total_amount = Column(DECIMAL(10, 2), nullable=False)
    status = Column(String(50), nullable=False)


Base.metadata.create_all(engine)


# =========================================================
# BASIC ROUTE
# =========================================================

@app.route("/")
def home():
    return jsonify({
        "status": "success",
        "message": "Boba Bliss API is running"
    })


@app.route("/favicon.ico")
def favicon():
    return "", 204


# =========================================================
# INVENTORY ROUTES
# =========================================================

@app.route("/inventory", methods=["GET"])
def get_inventory():
    session = None

    try:
        session = Session()
        products = session.query(Product).all()

        inventory = []

        for product in products:
            inventory.append({
                "product_code": product.product_code,
                "product_name": product.product_name,
                "brand": product.brand,
                "category": product.category,
                "stock": product.stock,
                "price": float(product.price)
            })

        return jsonify({
            "status": "success",
            "inventory": inventory
        })

    except Exception as error:
        return jsonify({
            "status": "failed",
            "message": str(error)
        }), 500

    finally:
        if session:
            session.close()


@app.route("/update_inventory", methods=["POST"])
def update_inventory():
    session = None

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "status": "failed",
                "message": "No JSON data received"
            }), 400

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
            return jsonify({
                "status": "failed",
                "message": "Product code not found"
            }), 404

        if product.stock < quantity:
            return jsonify({
                "status": "failed",
                "message": f"Insufficient stock. Available: {product.stock} units"
            }), 400

        product.stock -= quantity
        session.commit()

        return jsonify({
            "status": "success",
            "remaining_stock": product.stock,
            "product_code": product.product_code,
            "product_name": product.product_name,
            "brand": product.brand,
            "category": product.category,
            "price": float(product.price)
        })

    except Exception as error:
        if session:
            session.rollback()

        return jsonify({
            "status": "failed",
            "message": str(error)
        }), 500

    finally:
        if session:
            session.close()


# =========================================================
# PAYMENT ROUTE
# =========================================================

@app.route("/process_payment", methods=["POST"])
def process_payment():
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "status": "failed",
                "message": "No JSON data received"
            }), 400

        amount = float(data.get("amount", 0))
        product_name = data.get("product_name", "")
        quantity = int(data.get("quantity", 0))

        if amount <= 0 or quantity <= 0:
            return jsonify({
                "status": "failed",
                "message": "Invalid payment amount or quantity"
            }), 400

        transaction_id = f"TXN-{random.randint(100000, 999999)}"

        return jsonify({
            "status": "success",
            "transaction_id": transaction_id,
            "amount": round(amount, 2),
            "product_name": product_name,
            "quantity": quantity,
            "message": "Payment processed successfully"
        })

    except Exception as error:
        return jsonify({
            "status": "failed",
            "message": str(error)
        }), 500


# =========================================================
# ORDER ROUTES
# =========================================================

@app.route("/place_order", methods=["POST"])
def place_order():
    session = None

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "status": "failed",
                "message": "No JSON data received"
            }), 400

        product_code = data.get("product_code")
        quantity = int(data.get("quantity", 0))
        customer_name = data.get("customer_name", "Guest")

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
            return jsonify({
                "status": "failed",
                "message": "Product code not found"
            }), 404

        if product.stock < quantity:
            return jsonify({
                "status": "failed",
                "message": f"Insufficient stock. Available: {product.stock} units"
            }), 400

        price_per_unit = float(product.price)
        total_amount = quantity * price_per_unit

        # Simulated payment
        transaction_id = f"TXN-{random.randint(100000, 999999)}"

        # Update stock
        product.stock -= quantity

        # Save order
        new_order = Order(
            transaction_id=transaction_id,
            order_timestamp=datetime.now(),
            customer_name=customer_name,
            product_code=product.product_code,
            product_name=product.product_name,
            brand=product.brand,
            category=product.category,
            quantity=quantity,
            price_per_unit=price_per_unit,
            total_amount=total_amount,
            status="Completed"
        )

        session.add(new_order)
        session.commit()

        return jsonify({
            "status": "success",
            "transaction_id": transaction_id,
            "customer_name": customer_name,
            "product_code": product.product_code,
            "product_name": product.product_name,
            "brand": product.brand,
            "category": product.category,
            "quantity": quantity,
            "price_per_unit": price_per_unit,
            "total_amount": total_amount,
            "remaining_stock": product.stock,
            "message": "Order placed and payment processed successfully"
        })

    except Exception as error:
        if session:
            session.rollback()

        return jsonify({
            "status": "failed",
            "message": str(error)
        }), 500

    finally:
        if session:
            session.close()


@app.route("/order_history", methods=["GET"])
def order_history():
    session = None

    try:
        session = Session()

        orders = session.query(Order).order_by(Order.id.desc()).limit(20).all()

        result = []

        for order in orders:
            result.append({
                "id": order.id,
                "transaction_id": order.transaction_id,
                "timestamp": order.order_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "customer_name": order.customer_name,
                "product_code": order.product_code,
                "product_name": order.product_name,
                "brand": order.brand,
                "category": order.category,
                "quantity": order.quantity,
                "price_per_unit": float(order.price_per_unit),
                "total_amount": float(order.total_amount),
                "status": order.status
            })

        return jsonify({
            "status": "success",
            "orders": result
        })

    except Exception as error:
        return jsonify({
            "status": "failed",
            "message": str(error)
        }), 500

    finally:
        if session:
            session.close()


# =========================================================
# RUN LOCAL ONLY
# =========================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
