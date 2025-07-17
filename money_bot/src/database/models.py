from sqlalchemy import ForeignKey, Column, Integer, String, DateTime, Float
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Transaction(Base):
    __tablename__ = 'transactions'
    __table_args__ = {'schema': 'money_tracker', 'extend_existing': True}
    transaction_id = Column(Integer, primary_key=True, autoincrement=True)
    place = Column(String)
    receipt_date = Column(DateTime(timezone=True))
    mail_date = Column(DateTime(timezone=True), nullable=True)
    total = Column(Float)
    category_id = Column(Integer, ForeignKey('money_tracker.categories.category_id'), nullable=True)
    category = relationship('Category', backref='transactions')


class Category(Base):
    __tablename__ = 'categories'
    __table_args__ = {'schema': 'money_tracker', 'extend_existing': True}
    category_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, index=True)


class Subcategory(Base):
    __tablename__ = 'subcategories'
    __table_args__ = {'schema': 'money_tracker', 'extend_existing': True}
    subcategory_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, index=True)
    parent_id = Column(Integer, ForeignKey('money_tracker.categories.category_id'))
    parent = relationship('Category', backref='subcategories')
