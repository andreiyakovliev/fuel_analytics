from database import Base, engine
import models # noqa: F401 — import required to register the models

Base.metadata.create_all(bind=engine)
print("Tables created successfully") 