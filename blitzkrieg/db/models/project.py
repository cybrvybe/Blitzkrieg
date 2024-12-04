from sqlalchemy import UUID, Column, String, Boolean, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import relationship
from blitzkrieg.enums.project_types_enum import ProjectTypesEnum
from blitzkrieg.db.models.base import Base
import uuid

class Project(Base):
    __tablename__ = 'project'
    __table_args__ = {'schema': 'project_management'}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)
    github_repo = Column(String)
    directory_path = Column(String)
    is_deployed = Column(Boolean, default=False)
    deployment_date = Column(DateTime)
    pip_package_name = Column(String)
    parent_id = Column(UUID(as_uuid=True), ForeignKey('project_management.project.id'))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    short_description = Column(String, nullable=True)
    description = Column(String, nullable=True)
    project_type = Column(Enum(ProjectTypesEnum, name='projecttypesenum', create_constraint=False, native_enum=False))

    readme = relationship("Readme", back_populates="project")
    extrapolation = relationship("Extrapolation", back_populates="project", lazy='dynamic')
