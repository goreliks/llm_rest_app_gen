from flask import Flask, request, jsonify
import os
import openai

app = Flask(__name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise Exception("OPENAI_API_KEY not set in environment")

openai.api_key = OPENAI_API_KEY

@app.route('/api/generate_products', methods=['POST'])
def generate_products():
    try:
        data = request.get_json() or {}
        holiday = data.get("holiday")
        country = data.get("country", "US")
        target_audience = data.get("target_audience", "All")
        number_of_ideas = data.get("number_of_ideas", 10)

        if not holiday:
            return jsonify({"error": "Holiday is required for generating product ideas"}), 400

        prompt = (
            f"Generate {number_of_ideas} trending product ideas for the upcoming holiday '{holiday}' in {country} "
            f"for a target audience of {target_audience}. Provide only the product names as a list."
        )

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a product idea generator."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150
        )
        content = response["choices"][0]["message"]["content"]
        # Assume the response is a newline-separated list of product ideas.
        product_ideas = [line.strip("- ").strip() for line in content.splitlines() if line.strip()]
        return jsonify({"product_ideas": product_ideas})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5002, debug=True)
