import os
import datetime
import requests
from flask import Flask, request, jsonify
from pymongo import MongoClient

app = Flask(__name__)

# Setup MongoDB connection (using environment variable, defaulting to container name)
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongodb:27017/")
client = MongoClient(MONGO_URI)
db = client["trending_products_db"]
collection = db["recommendations"]

# Service URLs (using Docker Compose service names)
HOLIDAY_SERVICE_URL = os.environ.get("HOLIDAY_SERVICE_URL", "http://holiday_service:5001")
PRODUCT_SERVICE_URL = os.environ.get("PRODUCT_SERVICE_URL", "http://product_service:5002")
TREND_SERVICE_URL = os.environ.get("TREND_SERVICE_URL", "http://trend_service:5003")


@app.route('/api/trending-products', methods=['POST'])
def trending_products():
    try:
        data = request.get_json() or {}

        # Optional parameters with defaults or overrides
        target_country = data.get("target_country", "US")
        shipping_duration = int(data.get("shipping_duration", 30))
        popularity_threshold = float(data.get("popularity_threshold", 70))
        number_of_ideas = int(data.get("number_of_ideas", 10))
        historical_years = int(data.get("historical_years", 5))
        target_audience = data.get("target_audience", "All")

        # If a specific holiday is provided then use it; otherwise query holiday service.
        if "holiday" in data:
            if "holiday_date" not in data:
                return jsonify({"error": "holiday_date is required when overriding holiday"}), 400
            holiday_info = {
                "name": data["holiday"],
                "date": data["holiday_date"]
            }
        else:
            holiday_resp = requests.get(
                f"{HOLIDAY_SERVICE_URL}/api/holiday",
                params={"country": target_country, "sales_window": shipping_duration}
            )
            if holiday_resp.status_code != 200:
                return jsonify({"error": "Failed to retrieve holiday info"}), 500
            holiday_info = holiday_resp.json()

        holiday_name = holiday_info["name"]
        holiday_date_str = holiday_info["date"]
        # Validate/parse the holiday date.
        holiday_date = datetime.datetime.strptime(holiday_date_str, "%Y-%m-%d").date()

        # Generate product ideas using the Product Service.
        product_payload = {
            "holiday": holiday_name,
            "country": target_country,
            "target_audience": target_audience,
            "number_of_ideas": number_of_ideas
        }
        product_resp = requests.post(f"{PRODUCT_SERVICE_URL}/api/generate_products", json=product_payload)
        if product_resp.status_code != 200:
            return jsonify({"error": "Failed to generate product ideas"}), 500
        product_ideas = product_resp.json().get("product_ideas", [])

        validated_products = []
        # For each product idea, validate popularity using the Trend Service.
        for product in product_ideas:
            trend_params = {
                "product": product,
                "holiday_date": holiday_date_str,
                "sales_window": shipping_duration,
                "country": target_country,
                "historical_years": historical_years,
                "popularity_threshold": popularity_threshold
            }
            trend_resp = requests.get(f"{TREND_SERVICE_URL}/api/validate_trend", params=trend_params)
            if trend_resp.status_code != 200:
                continue  # Log error or skip product if trend check fails.
            trend_data = trend_resp.json()
            if trend_data.get("validated", False):
                validated_products.append({
                    "product": product,
                    "trend_score": trend_data.get("trend_score")
                })

        # Store the results in MongoDB.
        record = {
            "holiday": holiday_info,
            "validated_products": validated_products,
            "timestamp": datetime.datetime.utcnow()
        }
        result = collection.insert_one(record)

        return jsonify({
            "holiday": holiday_info,
            "validated_products": validated_products,
            "record_id": str(result.inserted_id)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
