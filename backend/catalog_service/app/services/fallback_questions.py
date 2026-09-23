"""Human-answerable questions when AI generation is unavailable."""
from ..schemas.domain import ClarifyingQuestionsCreate, DraftLocale


FIELDS = ("data", "expected_result", "success_criteria", "constraints", "users", "business_contact")
QUESTIONS = {
    "ru": (
        "Какие данные и материалы доступны для решения задачи?",
        "Какой конкретный результат вы хотите получить?",
        "По каким критериям вы будете оценивать успех решения?",
        "Какие есть ограничения по срокам, бюджету и технологиям?",
        "Кто будет пользоваться решением и какие у этих людей потребности?",
        "Кто со стороны бизнеса сможет отвечать на вопросы и как с ним связаться?",
    ),
    "kk": (
        "Тапсырманы шешу үшін қандай деректер мен материалдар қолжетімді?",
        "Қандай нақты нәтиже алғыңыз келеді?",
        "Шешімнің сәттілігін қандай өлшемдер бойынша бағалайсыз?",
        "Мерзім, бюджет және технологиялар бойынша қандай шектеулер бар?",
        "Шешімді кім пайдаланады және олардың қажеттіліктері қандай?",
        "Бизнес тарапынан сұрақтарға кім жауап бере алады және онымен қалай байланысуға болады?",
    ),
    "en": (
        "What data and materials are available to solve this task?",
        "What specific result would you like to receive?",
        "What criteria will you use to evaluate success?",
        "What constraints apply to the timeline, budget, and technologies?",
        "Who will use the solution and what are their needs?",
        "Who can answer questions on behalf of the business and how can they be contacted?",
    ),
}


def fallback_questions(locale: DraftLocale):
    # The original description already supplies context. Ask about the remaining
    # structured fields without claiming to have analyzed or inferred any facts.
    return ClarifyingQuestionsCreate.model_validate({"questions": [
        {"field": field, "question": question, "position": index}
        for index, (field, question) in enumerate(zip(FIELDS, QUESTIONS[locale]))
    ]}).questions
