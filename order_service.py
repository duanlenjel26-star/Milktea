from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

import requests
from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, DECIMAL, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker


app = Flask(__name__)
CORS(app)


# =========================================================
# SERVICE URLS
# =========================================================

INVENTORY_URL = "http://127.0.0.1:5001/update_inventory"
PAYMENT_URL = "http://127.0.0.1:5002/process_payment"


# =========================================================
# DATABASE CONNECTION
# =========================================================

engine = create_engine(
    "mysql+pymysql://root:@localhost/store_db",
    echo=False
)

Base = declarative_base()
Session = sessionmaker(bind=engine)


# =========================================================
# ORM MODEL
# =========================================================

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


# Create orders table if it does not exist yet
Base.metadata.create_all(engine)


# =========================================================
# ROUTES
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/favicon.ico")
def favicon():
    return "", 204


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

        # -------------------------------------------------
        # Step 1: Update inventory
        # -------------------------------------------------

        inv_payload = {
            "product_code": product_code,
            "quantity": quantity
        }

        inv_resp = requests.post(
            INVENTORY_URL,
            json=inv_payload,
            timeout=10
        )

        inv_data = inv_resp.json()

        if inv_data.get("status") != "success":
            return jsonify(inv_data), inv_resp.status_code

        product_name = inv_data["product_name"]
        brand = inv_data["brand"]
        category = inv_data["category"]
        price_per_unit = float(inv_data["price"])
        total_amount = quantity * price_per_unit

        # -------------------------------------------------
        # Step 2: Process payment
        # -------------------------------------------------

        pay_payload = {
            "amount": total_amount,
            "product_name": product_name,
            "quantity": quantity
        }

        pay_resp = requests.post(
            PAYMENT_URL,
            json=pay_payload,
            timeout=10
        )

        pay_data = pay_resp.json()

        if pay_data.get("status") != "success":
            return jsonify(pay_data), pay_resp.status_code

        transaction_id = pay_data["transaction_id"]

        # -------------------------------------------------
        # Step 3: Save order to MySQL using ORM
        # -------------------------------------------------

        session = Session()

        new_order = Order(
            transaction_id=transaction_id,
            order_timestamp=datetime.now(),
            customer_name=customer_name,
            product_code=product_code,
            product_name=product_name,
            brand=brand,
            category=category,
            quantity=quantity,
            price_per_unit=price_per_unit,
            total_amount=total_amount,
            status="Completed"
        )

        session.add(new_order)
        session.commit()

        # -------------------------------------------------
        # Step 4: Return JSON response
        # -------------------------------------------------

        return jsonify({
            "status": "success",
            "transaction_id": transaction_id,
            "customer_name": customer_name,
            "product_code": product_code,
            "product_name": product_name,
            "brand": brand,
            "category": category,
            "quantity": quantity,
            "price_per_unit": price_per_unit,
            "total_amount": total_amount,
            "remaining_stock": inv_data["remaining_stock"],
            "message": "Order placed and payment processed successfully"
        })

    except requests.exceptions.ConnectionError:
        return jsonify({
            "status": "failed",
            "message": "Cannot connect to inventory or payment service. Make sure ports 5001 and 5002 are running."
        }), 500

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

        # Only get latest 20 orders to reduce lag
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
# RUN APP
# =========================================================

if __name__ == "__main__":
    app.run(port=5000, debug=False)