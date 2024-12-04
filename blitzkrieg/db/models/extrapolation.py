import uuid
from blitzkrieg.db.models.base import Base
from sqlalchemy import UUID, Column, Enum, ForeignKey, Integer, String

from blitzkrieg.enums.extrapolation_types import ExtrapolationTypesEnum
from sqlalchemy.orm import relationship

class Extrapolation(Base):
    __tablename__ = 'extrapolation'
    __table_args__ = {'schema': 'project_management'}
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('project_management.project.id'))
    extrapolation_type = Enum(ExtrapolationTypesEnum, nullable=False)
    expert_level_content = Column(String)
    high_school_level_content = Column(String)
    toddler_level_content = Column(String)

    project = relationship("Project", back_populates="extrapolation")
