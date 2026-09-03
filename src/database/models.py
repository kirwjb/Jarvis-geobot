import datetime
from typing import Optional

from sqlalchemy import (
    String,
    Integer,
    Float,
    DateTime,
    Text,
    BigInteger,
    Boolean,
    Date,
    UniqueConstraint,
    ForeignKey,
    Column
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        index=True,
    )
    username: Mapped[Optional[str]] = mapped_column(String)
    tokens: Mapped[int] = mapped_column(Integer, default=5)
    last_reset: Mapped[datetime.date] = mapped_column(
        Date,
        default=datetime.date.today,
    )
    is_banned: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )


class OsmCache(Base):
    __tablename__ = "osm_cache"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    city: Mapped[str] = mapped_column(
        String,
        index=True,
    )
    sights_data: Mapped[Optional[str]] = mapped_column(
        Text,
    )
    name: Mapped[Optional[str]] = mapped_column(
        String,
    )
    address: Mapped[Optional[str]] = mapped_column(
        String,
    )
    lat: Mapped[Optional[float]] = mapped_column(
        Float,
    )
    lon: Mapped[Optional[float]] = mapped_column(
        Float,
    )


class Place(Base):
    """
    Основная таблица достопримечательностей.

    place_id — стабильный ID внешнего источника,
    например:
        osm:node:123456
        osm:way:987654
    """

    __tablename__ = "places"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    place_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    city: Mapped[str] = mapped_column(
        String(255),
        index=True,
        nullable=False,
    )

    region: Mapped[str] = mapped_column(
        String(255),
        index=True,
        nullable=False,
    )

    address: Mapped[str] = mapped_column(
        String(1000),
        default="",
        nullable=False,
    )

    category: Mapped[str] = mapped_column(
        String(100),
        default="misc",
        index=True,
        nullable=False,
    )

    lat: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    lon: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    hours: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    phone: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=datetime.datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=False,
    )


class Favorite(Base):
    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.user_id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    place_id: Mapped[str] = mapped_column(
        String,
        index=True,
    )

    place_name: Mapped[str] = mapped_column(
        String,
    )

    address: Mapped[str] = mapped_column(
        String,
    )

    lat: Mapped[float] = mapped_column(
        Float,
    )

    lon: Mapped[float] = mapped_column(
        Float,
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=datetime.datetime.utcnow,
    )


class History(Base):
    __tablename__ = "history"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.user_id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    query: Mapped[str] = mapped_column(
        String,
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=datetime.datetime.utcnow,
    )


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String,
        index=True,
    )

    owner_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.user_id",
            ondelete="CASCADE",
        ),
    )

    is_voting_active: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=datetime.datetime.utcnow,
    )


class GroupMember(Base):
    __tablename__ = "group_members"

    __table_args__ = (
        UniqueConstraint(
            "group_id",
            "user_id",
            name="uq_group_member",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("groups.id", ondelete="CASCADE"),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
    )

    role: Mapped[str] = mapped_column(
        String(20),
        default="member",
    )

    joined_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=datetime.datetime.utcnow,
    )


class GroupVote(Base):
    __tablename__ = "group_votes"

    __table_args__ = (
        UniqueConstraint(
            "group_id",
            "user_id",
            "place_id",
            name="uq_group_vote",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("groups.id", ondelete="CASCADE"),
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
    )

    place_id: Mapped[str] = mapped_column(
        String,
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=datetime.datetime.utcnow,
    )


class PlacePhoto(Base):
    __tablename__ = "place_photos"

    id = Column(Integer, primary_key=True)
    place_id = Column(String, ForeignKey("places.place_id"), nullable=False)
    source = Column(String, nullable=False)
    original_url = Column(String, nullable=False)
    local_url_thumb = Column(String, nullable=True)
    local_url_medium = Column(String, nullable=True)
    author = Column(String, nullable=True)
    license = Column(String, nullable=True)