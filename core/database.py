import os
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer
)

from sqlalchemy.orm import (
    declarative_base,
    sessionmaker
)


# Créer le dossier storage s'il n'existe pas
os.makedirs("storage", exist_ok=True)

engine = create_engine(
    "sqlite:///storage/database.db"
)

Base = declarative_base()


class PropertyDB(Base):

    __tablename__ = "properties"

    id = Column(String, primary_key=True)
    source = Column(String)
    title = Column(String)
    price = Column(Integer)
    url = Column(String)


Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)


def exists(property_id: str) -> bool:
    session = Session()
    result = session.query(PropertyDB).filter_by(id=property_id).first()
    session.close()
    return result is not None


def save(prop, uid: str):
    session = Session()
    obj = PropertyDB(
        id=uid,
        source=prop.source,
        title=prop.title,
        price=prop.price,
        url=prop.url
    )
    session.add(obj)
    session.commit()
    session.close()


def reset_db():
    """Supprimer toutes les annonces en base (remise à zéro)."""
    session = Session()
    session.query(PropertyDB).delete()
    session.commit()
    session.close()