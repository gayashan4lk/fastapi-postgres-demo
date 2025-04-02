from typing import Annotated, List

from fastapi import FastAPI, Depends, HTTPException, status, Response
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

class ChoiceResponse(BaseModel):
    id: int
    choice_text: str
    is_correct: bool
    
    class Config:
        orm_mode = True
        from_attributes = True

class QuestionResponse(BaseModel):
    id: int
    question_text: str
    choices: List[ChoiceResponse]
    
    class Config:
        orm_mode = True
        from_attributes = True

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

@app.post("/questions/", status_code=status.HTTP_201_CREATED, response_model=QuestionResponse)
async def create_question(question: QuestionsBase, response: Response, db: db_dependency):
    try:
        # Create the question
        db_question = models.Questions(question_text=question.question_text)
        db.add(db_question)
        db.commit()
        db.refresh(db_question)
        
        # Create the choices
        db_choices = []
        for choice in question.choices:
            db_choice = models.Choices(
                question_id=db_question.id,
                choice_text=choice.choice_text,
                is_correct=choice.is_correct
            )
            db.add(db_choice)
            db_choices.append(db_choice)
        
        db.commit()
        
        # Set the Location header
        response.headers["Location"] = f"/questions/{db_question.id}"
        
        # Return the created resource
        return db_question
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to create question: {str(e)}")

@app.get("/questions/", response_model=List[QuestionResponse])
async def get_questions(db: db_dependency):
    questions = db.query(models.Questions).all()
    return questions

@app.get("/questions/{question_id}", response_model=QuestionResponse)
async def get_question(question_id: int, db: db_dependency):
    question = db.query(models.Questions).filter(models.Questions.id == question_id).first()
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    return question

@app.put("/questions/{question_id}", response_model=QuestionResponse, status_code=status.HTTP_200_OK)
async def update_question(question_id: int, question: QuestionsBase, db: db_dependency):
    db_question = db.query(models.Questions).filter(models.Questions.id == question_id).first()
    if db_question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    
    try:
        # Update question text
        db_question.question_text = question.question_text
        
        # Delete existing choices
        db.query(models.Choices).filter(models.Choices.question_id == question_id).delete()
        
        # Create new choices
        for choice in question.choices:
            db_choice = models.Choices(
                question_id=question_id,
                choice_text=choice.choice_text,
                is_correct=choice.is_correct
            )
            db.add(db_choice)
        
        db.commit()
        db.refresh(db_question)
        return db_question
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to update question: {str(e)}")

@app.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(question_id: int, db: db_dependency):
    db_question = db.query(models.Questions).filter(models.Questions.id == question_id).first()
    if db_question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    
    try:
        # Delete associated choices first
        db.query(models.Choices).filter(models.Choices.question_id == question_id).delete()
        
        # Delete the question
        db.delete(db_question)
        db.commit()
        return None
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to delete question: {str(e)}")
