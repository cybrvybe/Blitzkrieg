from sqlalchemy import UUID, Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from blitzkrieg.db.models.base import Base

class LLMSystemPrompt(Base):
    __tablename__ = 'llm_system_prompt'
    __table_args__ = {'schema': 'project_management'}

    id = Column(UUID, primary_key=True)
    project_id = Column(UUID, ForeignKey('project_management.project.id'))
    prompt = Column(String)
    prompt_type = Column(String)
    prompt_category = Column(String)
    prompt_subcategory = Column(String)
    prompt_description = Column(String)
    prompt_example = Column(String)
