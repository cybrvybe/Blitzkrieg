import uuid
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from blitzkrieg.db.models.base import Base

class Readme(Base):
    __tablename__ = 'readme'
    __table_args__ = {'schema': 'project_management'}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('project_management.project.id'))
    content = Column(String)
    file_path = Column(String)
    file_name = Column(String)

    project = relationship("Project", back_populates="readme")
