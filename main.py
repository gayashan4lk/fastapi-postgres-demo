from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException
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

@app.get("/")
def read_root():
    return {"Hello": "World"}

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

@app.get("/questions/")
async def get_questions(db: db_dependency):
    return db.query(models.Questions).all()

@app.get("/questions/{question_id}")
async def get_question(question_id: int, db: db_dependency):
    result = db.query(models.Questions).filter(models.Questions.id == question_id).first()
    if result is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return result
