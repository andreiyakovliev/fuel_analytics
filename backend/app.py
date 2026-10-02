from flask import Flask, jsonify, request
from flask_cors import CORS
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from decimal import Decimal
import datetime
import jwt
import os
import re

from database import SessionLocal
from models import User, Profile, Trip, City

app = Flask(__name__)

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set in environment variables")
app.config["SECRET_KEY"] = SECRET_KEY

CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173"])

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
    token = jwt.encode(
        {"user_id": user_id, "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)},
        app.config["SECRET_KEY"], algorithm="HS256"
    )
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

def serialize_metric(val):
    if isinstance(val, Decimal):
        return float(val)
    return val

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

    hashed_password = generate_password_hash(password)

    session = SessionLocal()
    try:
        user = User(email=email, hash=hashed_password)
        session.add(user)
        session.flush()

        session.add(Profile(user_id=user.id, name=name))
        session.commit()
        user_id = user.id
    except IntegrityError:
        session.rollback()
        return jsonify({"error": "A user with this email already exists."}), 409
    except Exception:
        session.rollback()
        app.logger.exception("Registration error")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        session.close()

    token = create_token(user_id)
    return jsonify({"token": token, "message": "Registration successful"}), 201

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email") or "").strip().lower()
    password = data.get("password")

    if not email or not isinstance(password, str) or not password:
        return jsonify({"error": "Enter your email and password."}), 400

    session = SessionLocal()
    try:
        user = session.query(User).filter_by(email=email).first()
    finally:
        session.close()

    if not user or not user.hash or not check_password_hash(user.hash, password):
        return jsonify({"error": "Incorrect email or password"}), 401

    token = create_token(user.id)
    return jsonify({"token": token, "message": "Login successful"}), 200

@app.route("/api/cities", methods=["GET"])
@token_required
def get_cities(current_user_id):
    session = SessionLocal()
    try:
        cities = session.query(City).filter_by(user_id=current_user_id).order_by(City.name).all()
        return jsonify([{"id": c.id, "name": c.name} for c in cities]), 200
    except Exception:
        app.logger.exception("Error retrieving cities")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        session.close()

@app.route("/api/cities", methods=["POST"])
@token_required
def add_city(current_user_id):
    data = request.get_json(silent=True) or {}
    name = " ".join(str(data.get("name") or "").split())

    if not name or len(name) > 60:
        return jsonify({"error": "Invalid city name"}), 400

    session = SessionLocal()
    try:
        city = City(user_id=current_user_id, name=name, name_key=city_key(name))
        session.add(city)
        session.commit()
        city_id=city.id
    except IntegrityError as e:
        session.rollback()
        if getattr(e.orig, "sqlstate", None) == "23505" or getattr(e.orig, "pgcode", None) == "23505":
            return jsonify({"error": "City already exists"}), 409
        app.logger.exception("Unexpected integrity error adding city")
        return jsonify({"error": "Internal server error"}), 500
    except Exception:
        session.rollback()
        app.logger.exception("Error adding city")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        session.close()

    return jsonify({"id": city_id, "name": name}), 201

@app.route("/api/trips", methods=["GET"])
@token_required
def get_trips(current_user_id):
    session = SessionLocal()
    try:
        trips = session.query(Trip).filter_by(user_id=current_user_id).order_by(Trip.work_date.desc()).all()
        result = [{
            "id": t.id, 
            "work_date": t.work_date, 
            "city": t.city, 
            "distance_km": t.distance_km, 
            "fuel_cost": t.fuel_cost, 
            "fuel_price": t.fuel_price, 
            "rent_cost": t.rent_cost, 
            "other_expenses": t.other_expenses, 
            "work_hours": t.work_hours, 
            "income": t.income,
        } for t in trips]
        return jsonify(result), 200
    except Exception:
        app.logger.exception("Error retrieving trips")
        return jsonify({"error": "Error retrieving data from the database"}), 500
    finally:
        session.close()

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
        distance_km = float(data.get("distance_km", 0))
        fuel_cost = float(data.get("fuel_cost", 0))
        fuel_price= float(data.get("fuel_price", 0))
        rent_cost = float(data.get("rent_cost", 0))
        other_expenses = float(data.get("other_expenses", 0))
        work_hours = float(data.get("work_hours", 0))
        income = float(data.get("income", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "Numeric fields must contain valid numbers"}), 400

    numbers = [distance_km, fuel_cost, fuel_price, rent_cost, other_expenses, work_hours, income]

    if any(n < 0 for n in numbers):
        return jsonify({"error": "Numeric fields cannot be negative"}), 400
    session = SessionLocal()
    try:
        city_row = session.query(City).filter_by(user_id=current_user_id, name_key=city_key(city_in)).first()
        if not city_row:
            return jsonify({"error": "Unknown city. Add it first."}), 400
        trip = Trip(
            user_id=current_user_id, 
            work_date=work_date, 
            city=city_row.name, 
            distance_km=distance_km, 
            fuel_cost=fuel_cost, 
            fuel_price=fuel_price, 
            rent_cost=rent_cost, 
            other_expenses=other_expenses, 
            work_hours=work_hours, 
            income=income,
        )
        session.add(trip)
        session.commit()
        return jsonify({"status": "success", "message": "Record added successfully"}), 201
    except Exception:
        session.rollback()
        app.logger.exception("Error adding trip")
        return jsonify({"error": "Database write error"}), 500
    finally:
        session.close()

@app.route("/api/analytics", methods=["GET"])
@token_required
def get_analytics(current_user_id):
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    cities = request.args.get("cities")

    if start_date and not is_valid_date(start_date):
        return jsonify({"error": "start_date must be YYYY-MM-DD"}), 400
    
    if end_date and not is_valid_date(end_date):
        return jsonify({"error": "end_date must be YYYY-MM-DD"}), 400

    where_clauses = ["user_id = :user_id"]
    params = {"user_id": current_user_id}

    if start_date:
        where_clauses.append("work_date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        where_clauses.append("work_date <= :end_date")
        params["end_date"] = end_date

    session = SessionLocal()
    try:
        if cities:
            city_list = []
            for c in cities.split(","):
                c_clean = c.strip()
                if not c_clean:
                    continue
                row = session.query(City).filter_by(user_id=current_user_id, name_key=city_key(c_clean)).first()
                if row:
                    city_list.append(row.name)

            if not city_list:
                return jsonify({
                    "summary": {
                        "avg_net_income_per_day": None, 
                        "income_per_km": None, 
                        "net_income": None,
                        "net_income_per_km": None,
                        "total_distance": None, 
                        "total_expenses": None,
                        "total_hours": None, 
                        "total_income": None, 
                        "work_days": 0
                    },
                    "by_city": []
                }), 200

            placeholders = [f":city_{i}" for i in range(len(city_list))]
            for i, city in enumerate(city_list):
                params[f"city_{i}"] = city
            where_clauses.append(f"city IN({','.join(placeholders)})")

        where_sql = "WHERE " + " AND ".join(where_clauses)

        metrics_sql = """
            COUNT(DISTINCT work_date) as work_days,
            ROUND(SUM(income)::numeric, 2) as total_income,
            ROUND(SUM(fuel_cost + rent_cost + other_expenses)::numeric, 2) as total_expenses,
            ROUND((SUM(income) - SUM(fuel_cost + rent_cost + other_expenses))::numeric, 2) as net_income,
            ROUND(SUM(distance_km)::numeric, 2) as total_distance,
            ROUND(SUM(work_hours)::numeric, 2) as total_hours,
            ROUND((SUM(income) / NULLIF(SUM(distance_km), 0))::numeric, 2) as income_per_km,
            ROUND(((SUM(income) - SUM(fuel_cost + rent_cost + other_expenses)) / NULLIF(SUM(distance_km), 0))::numeric, 2) as net_income_per_km,
            ROUND(((SUM(income) - SUM(fuel_cost + rent_cost + other_expenses)) / NULLIF(COUNT(DISTINCT work_date), 0))::numeric, 2) as avg_net_income_per_day
        """

        summary_query = f"SELECT {metrics_sql} FROM trips {where_sql}"
        by_city_query = f"SELECT city, {metrics_sql} FROM trips {where_sql} GROUP BY city ORDER BY net_income DESC"

        summary_result = session.execute(text(summary_query), params).mappings().first()
        by_city_result = session.execute(text(by_city_query), params).mappings().all()

        return jsonify({
            "summary": {k: serialize_metric(v) for k, v in dict(summary_result).items()} if summary_result else {},
            "by_city": [
                {k: serialize_metric(v) for k, v in dict(r).items()}
                for r in by_city_result]
        }), 200
    except Exception:
        app.logger.exception("Analytics calculation error")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        session.close()

@app.route("/api/health")
def health_check():
    return jsonify({
        "status": "ok",
        "message": "Flask REST API works correctly"
    }), 200

if __name__ == "__main__":
    app.run(port=5000, debug=True)