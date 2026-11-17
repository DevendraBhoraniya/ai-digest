from app.database.models import Base
from app.database.session import engine

if __name__ == "__main__":
    Base.metadata.create_all(engine)
    print("tables created")