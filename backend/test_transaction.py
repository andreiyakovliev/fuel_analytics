import shutil
from cs50 import SQL

shutil.copy("fuel.db", "test.db")     # працюємо на копії
db = SQL("sqlite:///test.db")

def count_users():
    return db.execute("SELECT COUNT(*) AS n FROM users")[0]["n"]

before = count_users()

try:
    db.execute("BEGIN")
    user_id = db.execute(
        "INSERT INTO users (email, hash) VALUES (:email, :hash)",
        email="broken@test.com", hash="x"
    )
    # навмисно зламаний INSERT: колонки "nme" не існує
    db.execute(
        "INSERT INTO profiles (user_id, nme) VALUES (:user_id, :name)",
        user_id=user_id, name="Test"
    )
    db.execute("COMMIT")
except Exception as e:
    print("Помилка (очікувана):", e)
    # db.execute("ROLLBACK")

after = count_users()
print("Було:", before, "Стало:", after)
print("✅ Транзакція працює" if before == after else "❌ Запис у users залишився")