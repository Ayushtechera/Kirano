from sqlalchemy import text
from app.db.database import engine 

with engine.connect() as connection:
    print(connection.execute(text("SELECT 1")).scalar())