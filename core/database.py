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



engine = create_engine(
    "sqlite:///storage/database.db"
)


Base = declarative_base()



class PropertyDB(Base):

    __tablename__ = "properties"


    id = Column(
        String,
        primary_key=True
    )


    source = Column(
        String
    )


    title = Column(
        String
    )


    price = Column(
        Integer
    )


    url = Column(
        String
    )



Base.metadata.create_all(
    engine
)


Session = sessionmaker(
    bind=engine
)



def exists(property_id):

    session = Session()

    result = session.query(
        PropertyDB
    ).filter_by(
        id=property_id
    ).first()


    session.close()

    return result is not None



def save(prop):

    session = Session()


    obj = PropertyDB(

        id=prop.external_id,

        source=prop.source,

        title=prop.title,

        price=prop.price,

        url=prop.url

    )


    session.add(obj)

    session.commit()

    session.close()