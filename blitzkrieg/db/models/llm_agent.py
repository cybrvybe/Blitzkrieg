from blitzkrieg.db.models.base import Base
from sqlalchemy import Column, String, UUID, ForeignKey
import uuid

class LLMAgent(Base):
    __tablename__ = 'llm_agent'
    __table_args__ = {'schema': 'project_management'}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_name = Column(String)
    agent_description = Column(String)
    initial_system_prompt = Column(String)
    qa_system_prompt = Column(String)
    rewrite_system_prompt = Column(String)
