from typing import TypedDict, List, Dict, Union, Optional

class QuestionBase(TypedDict):
    question: str
    _id: int

class QuestionTextAnswer(TypedDict):
    answer: str
    lines: int

class QuestionText(QuestionBase):
    text: Dict[str, Union[str, QuestionTextAnswer]]

class QuestionSelect(QuestionBase):
    options: List[str]

class QuestionConnection(QuestionBase):
    connect: List[str]

Question = Union[QuestionText, QuestionSelect]

class Category(TypedDict):
    select: int
    questions: List[Question]

class Test(TypedDict):
    name: str
    includes: Optional[List[str]]
    categories: Dict[str, Category]

