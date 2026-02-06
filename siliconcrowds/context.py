from pydantic import BaseModel

from siliconcrowds.bucket import Bucket
from siliconcrowds.database import Database

class ContextPrompt(BaseModel):
    transcript: str
    image_url: str | None

class Answer(BaseModel):
    norways_answer: str
    actual_outcome: str | None
    answer_type: str | None

class Context(BaseModel):
    id: str
    question_id: str
    prompt: ContextPrompt
    answer: Answer

class Contextual:
    def __init__(self, bucket_name: str = "pilot_images", path: str = "pilot_images") -> None:
        database = Database()
        questions = database.get_questions()

        bucket = Bucket(bucket_name)
        signed_urls = bucket.list_public_urls(path=path)

        self.contexts: dict[str, Context] = {
            question.question_id: Context(
                id=str(question.id),
                question_id=question.question_id,
                prompt=ContextPrompt(
                    transcript=question.transcript,
                    image_url=signed_urls.get(question.question_id),
                ),
                answer=Answer(
                    norways_answer=question.norways_answer,
                    actual_outcome=question.actual_outcome,
                    answer_type=question.answer_type,
                ),
            )
            for question in questions
        }

    def __len__(self) -> int:
        return len(self.contexts)

    def __getitem__(self, question_id: str) -> Context:
        return self.contexts[question_id]

    def get_ids(self) -> list[str]:
        return list(self.contexts.keys())

if __name__ == "__main__":
    # uv run python -m siliconcrowds.context
    from rich import print as rich_print

    contextual = Contextual()
    ids: list[str] = contextual.get_ids()
    context: Context = contextual[ids[0]]

    print("================ Context: ==================")
    rich_print(context)