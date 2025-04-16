from flask import Flask, request, jsonify
import os
import requests
import datetime

app = Flask(__name__)

NINJAS_API_KEY = os.environ.get("NINJAS_API_KEY")
if not NINJAS_API_KEY:
    raise Exception("NINJAS_API_KEY not set in environment")

@app.route('/api/holiday', methods=['GET'])
def get_holiday():
    try:
        country = request.args.get("country", "US")
        sales_window = int(request.args.get("sales_window", 30))
        today = datetime.date.today()
        min_date = today + datetime.timedelta(days=sales_window)

        headers = {"X-Api-Key": NINJAS_API_KEY}
        params = {"country": country}
        response = requests.get("https://api.api-ninjas.com/v1/publicholidays", headers=headers, params=params)
        if response.status_code != 200:
            return jsonify({"error": "Error fetching holidays from Ninja API"}), 500
        holidays = response.json()
        upcoming_holidays = []
        for holiday in holidays:
            holiday_date = datetime.datetime.strptime(holiday["date"], "%Y-%m-%d").date()
            if holiday_date >= min_date:
                upcoming_holidays.append(holiday)
        if not upcoming_holidays:
            return jsonify({"error": "No upcoming holidays found with sufficient lead time"}), 404

        upcoming_holidays.sort(key=lambda x: x["date"])
        next_holiday = upcoming_holidays[0]
        return jsonify({
            "name": next_holiday["name"],
            "date": next_holiday["date"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001, debug=True)
