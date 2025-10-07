from sqlmodel import SQLModel, Session, create_engine, QueuePool

DATABASE_URL = "postgresql://postgres:mypass@localhost:5432/fastapi_db"


engine = create_engine(
    DATABASE_URL, 
    echo=True, 
    # poolclass=QueuePool,
    # pool_size=10,
    # max_overflow=20,
    # pool_pre_ping=True
)

# Dependency
def get_session():
    with Session(engine) as session:
        yield session

