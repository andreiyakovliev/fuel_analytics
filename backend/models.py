from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship
from database import Base

def utcnow():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__="users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    hash = Column(String)
    auth_provider = Column(String, default="local")
    created_at = Column(DateTime, default=utcnow)

    profile = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    trips = relationship("Trip", back_populates="user", cascade="all, delete-orphan")
    cities = relationship("City", back_populates="user", cascade="all, delete-orphan")

class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    name = Column(String)
    avatar_url = Column(String)
    location = Column(String)
    vehicle_type = Column(String, default="car")
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="profile")

class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    work_date = Column(String, nullable=False)
    city = Column(String, nullable=False)
    distance_km = Column(Float, default=0)
    fuel_cost = Column(Float, default=0)
    fuel_price = Column(Float, default=0)
    rent_cost = Column(Float, default=0)
    other_expenses = Column(Float, default=0)
    work_hours = Column(Float, default=0)
    income = Column(Float, default=0)
    created_at = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="trips")

class City(Base):
    __tablename__ = "cities"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    name_key = Column(String, nullable=False)

    user = relationship("User", back_populates="cities")

    __table_args__ = (UniqueConstraint("user_id", "name_key", name="uq_user_city"),)
