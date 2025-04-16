# Experiment MSc: Multi-Service Trending Products Application

This multi-service RESTful application helps online sellers identify trending products for upcoming holidays using historical demand data and AI-generated insights. It integrates with external APIs for public holidays (Ninja API), product idea generation (OpenAI API), and trend analysis (SERP API for Google Trends). Validated product recommendations are stored in MongoDB for further reference.

## Project Structure

experiment_msc/
├── orchestrator/
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── holiday_service/
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── product_service/
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── trend_service/
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml
└── README.md


## Configuration

The application requires the following environment variables:

- `NINJAS_API_KEY`: API key for the Ninja Public Holidays API.
- `OPENAI_API_KEY`: API key for OpenAI (for product idea generation).
- `SERP_API_KEY`: API key for the SERP API (for Google Trends data).
- `MONGO_URI`: (Optional) MongoDB connection URI (default is `mongodb://mongodb:27017/`).

You can set these variables in a `.env` file or export them in your environment before running Docker Compose.

## Building and Running the Application

1. **Clone the repository** and navigate to the project directory.
2. **Set environment variables** (for example, create a `.env` file at the project root):

    ```env
    NINJAS_API_KEY=your_ninjas_api_key
    OPENAI_API_KEY=your_openai_api_key
    SERP_API_KEY=your_serp_api_key
    ```

3. **Build and start the services** using Docker Compose:

    ```bash
    docker-compose up --build
    ```

4. The **Orchestrator API** will be available on `http://localhost:5050`.

## API Usage Examples

### 1. Default Settings

**Request:**

```bash
curl -X POST http://localhost:5050/api/trending-products \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Expected JSON Response:**
```json
{
  "holiday": {
    "name": "Thanksgiving",
    "date": "2025-11-27"
  },
  "validated_products": [
    {
      "product": "Pumpkin Spice Candle",
      "trend_score": 82.1
    },
    {
      "product": "Festive Table Runner",
      "trend_score": 75.3
    }
  ],
  "record_id": "640d0f2b5e3a3f1a8c9f0abc"
}
```

### 2. Override with Specific Holiday

**Request:**
```bash
curl -X POST http://localhost:5050/api/trending-products \
  -H "Content-Type: application/json" \
  -d '{
    "holiday": "Christmas",
    "holiday_date": "2025-12-25"
  }'
```

### 3. Override with Custom Shipping Duration and Popularity Threshold
**Request:**
```bash
curl -X POST http://localhost:5050/api/trending-products \
  -H "Content-Type: application/json" \
  -d '{
    "shipping_duration": 45,
    "popularity_threshold": 80
  }'
```

### 4. Override with Custom Number of Product Ideas and Historical Years
**Request:**
```bash
curl -X POST http://localhost:5050/api/trending-products \
  -H "Content-Type: application/json" \
  -d '{
    "number_of_ideas": 15,
    "historical_years": 3
  }'
```

**Typical Error Response:**

If an error occurs, the API returns JSON similar to:
```json
{
  "error": "Detailed error message describing what went wrong."
}
```

## Final Notes

To run the application:

1. Place each file in its corresponding folder according to the project tree shown above.
2. Set the required environment variables (`NINJAS_API_KEY`, `OPENAI_API_KEY`, `SERP_API_KEY`).
3. Run `docker-compose up --build` from the project root.
4. Use the provided `curl` examples (or your favorite REST client) to test the endpoint at `http://localhost:5050/api/trending-products`.

This complete code example demonstrates how to coordinate multiple REST services that call external APIs, validate product trends, and store results in MongoDB while providing flexible API overrides and robust error handling.
