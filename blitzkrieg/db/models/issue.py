# sql alchemy model for project issues called issues

from sqlalchemy import UUID, Column, Integer, String, ForeignKey, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from blitzkrieg.db.models.base import Base
class Issue(Base):
    __tablename__ = 'issue'

    __table_args__ = {'schema': 'project_management'}

    id = Column(UUID, primary_key=True)
    index=Column(Integer)
    branch_name = Column(String)
    title = Column(String)
    description = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    project_id = Column(UUID, ForeignKey('project_management.project.id'))
    content = Column(String)

    project = relationship('Project')
