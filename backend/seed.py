import datetime
from cs50 import SQL
from werkzeug.security import generate_password_hash

db = SQL("sqlite:///fuel.db")

def seed():
    # 1. Очищаємо таблиці перед заповненням, щоб не дублювати дані
    db.execute("DELETE FROM trips")
    db.execute("DELETE FROM profiles")
    db.execute("DELETE FROM users")
    db.execute("DELETE FROM sqlite_sequence")

    # 2. Створюємо тестового користувача
    hashed_pw = generate_password_hash("password123")
    user_id = db.execute(
        "INSERT INTO users (email, hash) VALUES (:email, :hash)",
        email="demo@example.com",
        hash=hashed_pw
    )

    # 3. Створюємо профіль для нього
    db.execute(
        "INSERT INTO profiles (user_id, name, location, vehicle_type) VALUES (:user_id, :name, :location, :vehicle)",
        user_id=user_id,
        name="Тестовий Водій",
        location="Київ",
        vehicle="car"
    )

    # 4. Додаємо тестові поїздки
    today = datetime.date.today()
    trips_data = [
        (str(today - datetime.timedelta(days=2)), "Київ", 120.5, 450.0, 52.5, 0, 50, 8.5, 2400.0),
        (str(today - datetime.timedelta(days=1)), "Київ", 95.0, 380.0, 53.0, 0, 0, 7.0, 1900.0),
        (str(today), "Бровари", 140.0, 510.0, 52.0, 0, 30, 9.0, 2800.0)
    ]

    for trip in trips_data:
        db.execute(
            """
            INSERT INTO trips (user_id, work_date, city, distance_km, fuel_cost, fuel_price, rent_cost, other_expenses, work_hours, income)
            VALUES (:user_id, :work_date, :city, :distance_km, :fuel_cost, :fuel_price, :rent_cost, :other_expenses, :work_hours, :income)
            """,
            user_id=user_id, work_date=trip[0], city=trip[1], distance_km=trip[2],
            fuel_cost=trip[3], fuel_price=trip[4], rent_cost=trip[5],
            other_expenses=trip[6], work_hours=trip[7], income=trip[8]
        )

    print("Базу заповнено!")
    print("Тестовий акаунт: demo@example.com / password123")

if __name__ == "__main__":
    seed()