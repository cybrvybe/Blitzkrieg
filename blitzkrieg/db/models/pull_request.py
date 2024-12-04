from sqlalchemy import UUID, Column, Integer, String, DateTime, ForeignKey
from blitzkrieg.db.models.base import Base

class PullRequest(Base):
    __tablename__ = 'pull_request'
    __table_args__ = {'schema': 'project_management'}

    id = Column(Integer, primary_key=True)
    project_id = Column(UUID, ForeignKey('project_management.project.id'))  # Only foreign key reference
    pr_number = Column(Integer)
    title = Column(String)
    state = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    body = Column(String)
