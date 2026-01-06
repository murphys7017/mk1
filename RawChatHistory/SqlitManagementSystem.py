from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.dialects.sqlite import JSON

from DataClass.ChatMessage import ChatMessage
from DataClass.DialogueMessage import DialogueMessage

Base = declarative_base()


class ChatMessageModel(Base):
    __tablename__ = 'chat_messages'

    chat_turn_id = Column(Integer, primary_key=True, autoincrement=True)
    role = Column(String)
    content = Column(String)
    timestamp = Column(Integer)
    timedate = Column(String)
    media_type = Column(String)
    extra = Column(JSON)
    def __repr__(self):
        return f"<ChatMessage(chat_turn_id={self.chat_turn_id}, role={self.role}, content={self.content}, timestamp={self.timestamp}, timedate={self.timedate}, media_type={self.media_type}, extra={self.extra})>" 
	



class DialogueMessageModel(Base):
    __tablename__ = 'dialogue_messages'

    dialogue_id = Column(Integer, primary_key=True, autoincrement=True)
    is_completed = Column(Boolean, default=False)
    dialogue_turns = Column(Integer)
    start_turn_id = Column(Integer)
    end_turn_id = Column(Integer)
    summary = Column(String)

    def __repr__(self):
        return f"<DialogueMessage(dialogue_id={self.dialogue_id}, is_completed={self.is_completed}, dialogue_turns={self.dialogue_turns}, start_turn_id={self.start_turn_id}, end_turn_id={self.end_turn_id}, summary={self.summary})>"


class SqlitManagementSystem:
    def __init__(self, db_path: str, echo: bool = True):
        self.db_path = db_path
        self.engine = create_engine(f'sqlite:///{self.db_path}', echo=echo)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def chat_message2model(self, message: ChatMessage) -> ChatMessageModel:
        return ChatMessageModel(
            chat_turn_id=message.chat_turn_id,
            role=message.role,
            content=message.content,
            timestamp=message.timestamp,
            timedate=message.timedate,
            media_type=message.media_type,
            extra=message.extra
        )
    def dialogue_message2model(self, message: DialogueMessage) -> DialogueMessageModel:
        return DialogueMessageModel(
            dialogue_id=message.dialogue_id,
            is_completed=message.is_completed,
            dialogue_turns=message.dialogue_turns,
            start_turn_id=message.start_turn_id,
            end_turn_id=message.end_turn_id,
            summary=message.summary
        )
    def chat_model2message(self, model: ChatMessageModel) -> ChatMessage:
        return ChatMessage(
            chat_turn_id=model.chat_turn_id,
            role=model.role,
            content=model.content,
            timestamp=model.timestamp,
            timedate=model.timedate,
            media_type=model.media_type,
            extra=model.extra
        )
    def dialogue_model2message(self, model: DialogueMessageModel) -> DialogueMessage:
        return DialogueMessage(
            dialogue_id=model.dialogue_id,
            is_completed=model.is_completed,
            dialogue_turns=model.dialogue_turns,
            start_turn_id=model.start_turn_id,
            end_turn_id=model.end_turn_id,
            summary=model.summary
        )

    # def load_history(self):
    #     session = self.Session()
    #     chat_messages = session.query(ChatMessageModel).order_by(ChatMessageModel.chat_turn_id.desc()).limit(self.history_length).all()
    #     dialogue_messages = session.query(DialogueMessageModel).order_by(DialogueMessageModel.dialogue_id.desc()).limit(self.history_length).all()
        
    #     return chat_messages, dialogue_messages
    
    def getHistoryLength(self) -> int:
        session = self.Session()
        count = session.query(ChatMessageModel).count()
        session.close()
        return count
    
    def getHistory(self,length) -> list[ChatMessage]:
        session = self.Session()
        chatMs = session.query(ChatMessageModel).order_by(ChatMessageModel.chat_turn_id.desc()).limit(length).all()
        session.close()
        chat = []
        for chatM in chatMs:
            chat.append(self.chat_model2message(chatM))
        chat_messages = list(reversed(chat))
        
        return chat_messages
    
    def getDialogues(self, length: int) -> list[DialogueMessage]:
        session = self.Session()
        dialogueMs = session.query(DialogueMessageModel).order_by(DialogueMessageModel.dialogue_id.desc()).limit(length).all()
        session.close()
        dialogue = []
        for dialogueM in dialogueMs:
            dialogue.append(self.dialogue_model2message(dialogueM))
        dialogue_messages = list(reversed(dialogue))
        return dialogue_messages
    
    def getDialoguesById(self, dialogue_id: int) -> DialogueMessage:
        session = self.Session()
        dialogue = session.query(DialogueMessageModel).filter(DialogueMessageModel.dialogue_id == dialogue_id).first()
        session.close()
        return self.dialogue_model2message(dialogue)
    
    def updateDialogue(self, dialogue: DialogueMessage):
        session = self.Session()
        existing_dialogue = session.query(DialogueMessageModel).filter(DialogueMessageModel.dialogue_id == dialogue.dialogue_id).first()
        if existing_dialogue:
            existing_dialogue.is_completed = dialogue.is_completed
            existing_dialogue.dialogue_turns = dialogue.dialogue_turns
            existing_dialogue.start_turn_id = dialogue.start_turn_id
            existing_dialogue.end_turn_id = dialogue.end_turn_id
            existing_dialogue.summary = dialogue.summary
            session.commit()
        session.close()
    
    def addDialogue(self, dialogue: DialogueMessage):
        session = self.Session()
        dialogue_model = self.dialogue_message2model(dialogue)
        session.add(dialogue_model)
        session.commit()
    
    def addMessage(self, message: ChatMessage):
        session = self.Session()
        message_model = self.chat_message2model(message)
        session.add(message_model)
        session.commit()

    def exit(self):
        self.engine.dispose()
