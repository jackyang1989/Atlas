from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text
from sqlalchemy.sql import func
from app.database import Base


class Domain(Base):
    __tablename__ = "domains"
    
    id = Column(String(36), primary_key=True)
    domain = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(100), nullable=False)
    
    provider = Column(String(50), default="standalone")
    api_key = Column(Text, nullable=True)
    api_secret = Column(Text, nullable=True)
    
    auto_renew = Column(Boolean, default=True)
    renew_before_days = Column(Integer, default=30)
    
    cert_valid_from = Column(DateTime, nullable=True)
    cert_valid_to = Column(DateTime, nullable=True)
    last_renew_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Domain {self.domain}>"
