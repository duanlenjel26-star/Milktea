from flask import Flask, request, jsonify
from flask_cors import CORS
import random


app = Flask(__name__)
CORS(app)


@app.route("/process_payment", methods=["POST"])
def process_payment():
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


if __name__ == "__main__":
    app.run(port=5002, debug=True)