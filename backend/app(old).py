from cs50 import SQL
from flask import Flask, jsonify, request
from flask_cors import CORS
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import re


app = Flask(__name__)
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set in environment variables")
app.config["SECRET_KEY"] = SECRET_KEY

CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173"])

db = SQL("sqlite:///fuel.db")

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if "Authorization" in request.headers:
            auth_header = request.headers["Authorization"]
            parts = auth_header.split(" ", 1)
            if len(parts) == 2 and parts[0] == "Bearer":
                token = parts[1]

        if not token:
            return jsonify({"error": "Authorization token is missing"}), 401

        try:
            data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            current_user_id = data.get("user_id")

            if current_user_id is None:
                return jsonify({"error": "Invalid token"}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "The token has expired."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        return f(current_user_id, *args, **kwargs)

    return decorated

def create_token(user_id):
    token = jwt.encode({"user_id": user_id, "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)}, app.config["SECRET_KEY"], algorithm="HS256")
    return token

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def is_valid_email(email):
    return bool(EMAIL_RE.match(email))

def is_valid_date(value):
    try:
        datetime.date.fromisoformat(value)
        return True
    except (ValueError, TypeError):
        return False

def city_key(name):
    return " ".join(name.split()).casefold()

@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email") or "").strip().lower()
    password = data.get("password")
    name = str(data.get("name") or "").strip()

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    if not is_valid_email(email):
        return jsonify({"error":"Invalid email format"}), 400

    if not isinstance(password, str) or len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    existing_user = db.execute("SELECT id FROM users WHERE email = :email", email=email)
    if existing_user:
        return jsonify({"error": "A user with this email already exists."}), 409

    hashed_password = generate_password_hash(password)

    try:
        db.execute("BEGIN")
        user_id = db.execute("INSERT INTO users (email, hash) VALUES (:email, :hash)", email=email, hash=hashed_password)
        db.execute("INSERT INTO profiles (user_id, name) VALUES (:user_id, :name)", user_id=user_id, name=name)
        db.execute("COMMIT")

    except ValueError:
        return jsonify({"error": "A user with this email already exists."}), 409
    except Exception:
        app.logger.exception("Registration error")
        return jsonify({"error": "Internal server error"}), 500

    token = create_token(user_id)

    return jsonify({"token": token, "message": "Registration successful"}), 201

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email") or "").strip().lower()
    password = data.get("password")

    if not email or not isinstance(password, str) or not password:
        return jsonify({"error": "Enter your email and password."}), 400

    users = db.execute("SELECT * FROM users WHERE email = :email", email=email)

    if not users or not check_password_hash(users[0]["hash"], password):
        return jsonify({"error": "Incorrect email or password"}), 401

    user_id = users[0]["id"]
    token = create_token(user_id)

    return jsonify({"token": token, "message": "Login successful"}), 200

@app.route("/api/cities", methods=["GET"])
@token_required
def get_cities(current_user_id):
    try:
        rows = db.execute("SELECT id, name FROM cities WHERE user_id = :user_id ORDER BY name", user_id=current_user_id)
        return jsonify(rows), 200
    except Exception:
        app.logger.exception("Error retrieving cities")
        return jsonify({"error": "Error retrieving data from the database"}), 500

@app.route("/api/cities", methods=["POST"])
@token_required
def add_city(current_user_id):
    data = request.get_json(silent=True) or {}
    name = " ".join(str(data.get("name") or "").split())

    if not name or len(name) > 60:
        return jsonify({"error": "Invalid city name"}), 400

    try:
        city_id = db.execute("INSERT INTO cities (user_id, name, name_key) VALUES (:user_id, :name, :name_key)", user_id=current_user_id, name=name, name_key=city_key(name))
    except ValueError:
        return jsonify({"error": "City already exists"}), 409
    except Exception:
        app.logger.exception("Error adding city")
        return jsonify({"error": "Internal server error"}), 500

    return jsonify({"id": city_id, "name": name}), 201

@app.route("/api/trips", methods=["GET"])
@token_required
def get_trips(current_user_id):
    try:
        trips = db.execute("SELECT * FROM trips WHERE user_id = :user_id ORDER BY work_date DESC", user_id = current_user_id)
        return jsonify(trips), 200
    except Exception:
        app.logger.exception("Error retrieving trips")
        return jsonify({"error": "Error retrieving data from the database"}), 500

@app.route("/api/trips", methods=["POST"])
@token_required
def add_trip(current_user_id):
    data = request.get_json(silent=True) or {}

    if not data:
        return jsonify({"error": "Invalid or missing JSON in the request body"}), 400
    
    work_date = data.get("work_date")

    if not work_date:
        return jsonify({"error": "The 'work_date' field is mandatory"}), 400

    if not is_valid_date(work_date):
        return jsonify({"error": "work_date must be YYYY-MM-DD"}), 400

    city_in = " ".join(str(data.get("city") or "").split())
    if not city_in:
        return jsonify({"error": "The 'city' field is mandatory"}), 400

    try:
        row = db.execute(
            "SELECT name FROM cities WHERE user_id = :user_id AND name_key = :name_key",
            user_id=current_user_id, name_key=city_key(city_in)
        )
    except Exception:
        app.logger.exception("Error looking up city")
        return jsonify({"error": "Internal server error"}), 500

    if not row:
        return jsonify({"error": "Unknown city. Add it first."}), 400
    
    city = row[0]["name"]

    try:
        distance_km = float(data.get("distance_km", 0))
        fuel_cost = float(data.get("fuel_cost", 0))
        fuel_price = float(data.get("fuel_price", 0))
        rent_cost = float(data.get("rent_cost", 0))
        other_expenses = float(data.get("other_expenses", 0))
        work_hours = float(data.get("work_hours", 0))
        income = float(data.get("income", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "Numeric fields must contain valid numbers"}), 400

    numbers = [distance_km, fuel_cost, fuel_price, rent_cost, other_expenses, work_hours, income]

    if any(n < 0 for n in numbers):
        return jsonify({"error": "Numeric fields cannot be negative"}), 400

    try:
        db.execute(
            """
            INSERT INTO trips (user_id, work_date, city, distance_km, fuel_cost, fuel_price, rent_cost, other_expenses, work_hours, income)
            VALUES(:user_id, :work_date, :city, :distance_km, :fuel_cost, :fuel_price, :rent_cost, :other_expenses, :work_hours, :income)
            """, user_id=current_user_id, work_date=work_date, city=city, distance_km=distance_km, fuel_cost=fuel_cost, fuel_price=fuel_price, rent_cost=rent_cost, other_expenses=other_expenses, work_hours=work_hours, income=income
        )
        return jsonify({"status": "success", "message": "Record added successfully"}), 201
    except Exception:
        app.logger.exception("Error adding trip")
        return jsonify({"error": "Database write error"}), 500

@app.route("/api/analytics", methods=["GET"])
@token_required
def get_analytics(current_user_id):
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    cities = request.args.get("cities")

    where_clauses = ["user_id = :user_id"]
    params = {"user_id": current_user_id}

    if start_date and not is_valid_date(start_date):
        return jsonify({"error": "start_date must be YYYY-MM-DD"}), 400
    
    if end_date and not is_valid_date(end_date):
        return jsonify({"error": "end_date must be YYYY-MM-DD"}), 400

    if start_date:
        where_clauses.append("work_date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        where_clauses.append("work_date <= :end_date")
        params["end_date"] = end_date
    try:
        if cities:
            city_list = []
            for c in cities.split(","):
                c_clean = c.strip()
                if not c_clean:
                    continue
                row = db.execute(
                    "SELECT name FROM cities WHERE user_id = :user_id AND name_key = :name_key", user_id=current_user_id, name_key=city_key(c_clean)
                )
                if row:
                    city_list.append(row[0]["name"])

            if city_list:
                placeholders = [f":city_{i}" for i in range(len(city_list))]
                for i, city in enumerate(city_list):
                    params[f"city_{i}"] = city
                where_clauses.append(f"city IN ({','.join(placeholders)})")
            else:
                return jsonify({
                    "summary": {
                        "avg_net_income_per_day": None, "income_per_km": None, "net_income": None,
                        "net_income_per_km": None, "total_distance": None, "total_expenses": None,
                        "total_hours": None, "total_income": None, "work_days": 0
                    },
                    "by_city": []
                }), 200
        
        where_sql = "WHERE " + " AND ".join(where_clauses)

        metrics_sql = """
            COUNT(DISTINCT work_date) as work_days,
            ROUND(SUM(income), 2) as total_income,
            ROUND(SUM(fuel_cost + rent_cost + other_expenses), 2) as total_expenses,
            ROUND(SUM(income) - SUM(fuel_cost + rent_cost + other_expenses), 2) as net_income,
            ROUND(SUM(distance_km), 2) as total_distance,
            ROUND(SUM(work_hours), 2) as total_hours,
            ROUND(SUM(income) / NULLIF(SUM(distance_km), 0), 2) as income_per_km,
            ROUND((SUM(income) - SUM(fuel_cost + rent_cost + other_expenses)) / NULLIF(SUM(distance_km), 0), 2) as net_income_per_km,
            ROUND((SUM(income) - SUM(fuel_cost + rent_cost + other_expenses)) / NULLIF(COUNT(DISTINCT work_date), 0), 2) as avg_net_income_per_day
        """

        summary_query = f"SELECT {metrics_sql} FROM trips {where_sql}"
        by_city_query = f"SELECT city, {metrics_sql} FROM trips {where_sql} GROUP BY city ORDER BY net_income DESC"

        summary_result = db.execute(summary_query, **params)[0]
        by_city_result = db.execute(by_city_query, **params)

        return jsonify({
            "summary": summary_result,
            "by_city": by_city_result
        }), 200
    except Exception:
        app.logger.exception("Analytics calculation error")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/api/health")
def health_check():
    return jsonify({
        "status": "ok",
        "message": "Flask REST API works correctly"
    }), 200

if __name__ == "__main__":
    app.run(port=5000)