from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Float, ForeignKey

Base = declarative_base()

class Picture(Base):
    __tablename__ = 'pictures'
    
    id = Column(String(36), primary_key=True)
    path = Column(String(255), nullable=False)
    date = Column(String(19), nullable=False)

class Tag(Base):
    __tablename__ = 'tags'
    
    tag = Column(String(32), primary_key=True)
    picture_id = Column(String(36), ForeignKey('pictures.id'), primary_key=True)
    confidence = Column(Float, nullable=False)
    date = Column(String(19), nullable=False)
