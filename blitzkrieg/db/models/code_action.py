from sqlalchemy import UUID, Column, Enum, Integer, String, ForeignKey

from blitzkrieg.enums.code_action import CodeActionTypeEnum

from blitzkrieg.db.models.base import Base

class CodeAction(Base):
    __tablename__ = 'code_action'
    __table_args__ = {'schema': 'project_management'}

    id = Column(UUID, primary_key=True)
    project_id = Column(UUID, ForeignKey('project_management.project.id'))
    code_action_type = Column(Enum(CodeActionTypeEnum), nullable=False)
    ai_system_description = Column(String)
    content = Column(String)
