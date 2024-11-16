from typing import TypedDict, List, Dict, Union, Optional

class QuestionBase(TypedDict):
    question: str
    _id: int

class QuestionText(QuestionBase):
    text: Dict[str, str]

class QuestionSelect(QuestionBase):
    options: List[str]

class Category(TypedDict):
    select: int
    questions: List[QuestionBase]

class Test(TypedDict):
    name: str
    includes: Optional[List[str]]
    categories: Dict[str, Category]

Question = Union[QuestionText, QuestionSelect]
