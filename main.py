from typing import Annotated

from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

import models
from database import engine, SessionLocal

app = FastAPI()

models.Base.metadata.create_all(bind=engine)

class ChoicesBase(BaseModel):
    choice_text: str
    is_correct: bool

class QuestionsBase(BaseModel):
    question_text: str
    choices: list[ChoicesBase]

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

@app.post("/questions/")
async def create_question(question: QuestionsBase, db: db_dependency):
    db_question = models.Questions(question_text=question.question_text)
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    for choice in question.choices:
        db_choice = models.Choices(
            question_id=db_question.id,
            choice_text=choice.choice_text,
            is_correct=choice.is_correct
        )
        db.add(db_choice)
    db.commit()
    db.refresh(db_choice)

@app.get("/")
def read_root():
    return {"Hello": "World"}
