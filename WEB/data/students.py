from sqlalchemy import Column, Integer, String
from models import db_session
from models.db_session import SqlAlchemyBase


class Students(SqlAlchemyBase):
    __tablename__ = 'students'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    place = Column(String, nullable=False)
    author = Column(Integer, nullable=False)
