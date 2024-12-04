from blitzkrieg.db.models.base import Base
from sqlalchemy import UUID, Column, Enum, ForeignKey, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship

from blitzkrieg.enums.chat_message_sender_types import ChatMessageSenderTypes

class ChatMessage(Base):
    __tablename__ = 'chat_message'
    __table_args__ = {'schema': 'project_management'}

    id = Column(UUID(as_uuid=True), primary_key=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey('project_management.conversation.id'))
    sender = Enum(ChatMessageSenderTypes)
    message = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    is_read = Column(Boolean)

    conversation = relationship("Conversation", back_populates="chat_messages")
