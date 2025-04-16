from flask import Flask, request, jsonify
import os
import requests
import datetime
import statistics

app = Flask(__name__)

SERP_API_KEY = os.environ.get("SERP_API_KEY")
if not SERP_API_KEY:
    raise Exception("SERP_API_KEY not set in environment")


@app.route('/api/validate_trend', methods=['GET'])
def validate_trend():
    try:
        product = request.args.get("product")
        holiday_date_str = request.args.get("holiday_date")
        sales_window = int(request.args.get("sales_window", 30))
        country = request.args.get("country", "US")
        historical_years = int(request.args.get("historical_years", 5))
        popularity_threshold = float(request.args.get("popularity_threshold", 70))

        if not product or not holiday_date_str:
            return jsonify({"error": "Missing required parameters"}), 400

        holiday_date = datetime.datetime.strptime(holiday_date_str, "%Y-%m-%d").date()
        trend_scores = []

        # For each of the past N years, compute the average search score over the sales window.
        for i in range(1, historical_years + 1):
            past_year = holiday_date.year - i
            past_holiday_date = holiday_date.replace(year=past_year)
            start_date = past_holiday_date - datetime.timedelta(days=sales_window)
            end_date = past_holiday_date

            start_date_str = start_date.strftime("%Y-%m-%d")
            end_date_str = end_date.strftime("%Y-%m-%d")

            # Call SERP API for Google Trends data.
            params = {
                "engine": "google_trends",
                "q": product,
                "hl": "en",
                "geo": country,
                "date": f"{start_date_str} {end_date_str}",
                "api_key": SERP_API_KEY
            }
            serp_response = requests.get("https://serpapi.com/search", params=params)
            if serp_response.status_code != 200:
                continue
            serp_data = serp_response.json()
            # Assume a field 'trend_scores' with a list of daily scores is returned.
            daily_scores = serp_data.get("trend_scores", [])
            if daily_scores:
                avg_score = statistics.mean(daily_scores)
                trend_scores.append(avg_score)

        if not trend_scores:
            return jsonify({"validated": False, "trend_score": 0, "message": "No trend data available"}), 200

        overall_mean = statistics.mean(trend_scores)
        validated = overall_mean >= popularity_threshold

        return jsonify({
            "validated": validated,
            "trend_score": overall_mean
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5003, debug=True)
