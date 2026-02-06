import re

from pydantic import BaseModel
from datetime import datetime

from siliconcrowds.model import Message, MessageRole, MessageType


class Persona(BaseModel):
    id: int
    age_range: str
    gender: str
    ethnicity: str
    education: str
    politics: str
    weight: float

    def to_prompt(self) -> str:
        return (
            f"You are a {self.gender} aged {self.age_range} "
            f"with {self.ethnicity}. "
            f"Your education level is {self.education.lower()}. "
            f"Your political views are {self.politics}."
        )


class Prompt(BaseModel):
    id: int
    category: str
    system_prompt: str
    user_prompt: str
    template_name: str
    description: str | None


class Question(BaseModel):
    id: int
    question_id: str
    transcript: str
    image_path: str
    norways_answer: str
    actual_outcome: str | None
    air_date: datetime | None
    answer_type: str | None


class Instruction:

    def __init__(self) -> None:
        from siliconcrowds.database import Database
        database = Database()
        self.baseline_prompts = database.get_baseline_prompts()
        self.generic_persona_prompts = database.get_generic_persona_prompts()
        self.specific_persona_prompts = database.get_specific_persona_prompts()

    def _get_prompt(self, prompts: dict[str, Prompt], prompt_name: str) -> Prompt:
        if prompt_name not in prompts:
            raise ValueError(f"Prompt with name {prompt_name} not found")
        return prompts[prompt_name]

    def get_baseline_prompt(self, prompt_name: str) -> Prompt:
        return self._get_prompt(self.baseline_prompts, prompt_name)

    def get_generic_persona_prompt(self, prompt_name: str) -> Prompt:
        return self._get_prompt(self.generic_persona_prompts, prompt_name)

    def get_specific_persona_prompt(self, prompt_name: str) -> Prompt:
        return self._get_prompt(self.specific_persona_prompts, prompt_name)

    @staticmethod
    def build_message(prompt: Prompt, transcript: str, image_url: str | None = None) -> list[Message]:
        formatted_user_prompt = prompt.user_prompt.format(transcript=transcript, image="")
        formatted_user_prompt = re.sub(r'\n*###IMAGE###\n.*?\n*', '', formatted_user_prompt).rstrip()

        messages = [
            Message(
                role=MessageRole.SYSTEM,
                content=[{"type": MessageType.TEXT.value, "text": prompt.system_prompt}]
            ),
            Message(
                role=MessageRole.USER,
                content=[{"type": MessageType.TEXT.value, "text": formatted_user_prompt}]
            ),
        ]

        if image_url:
            messages.append(Message(
                role=MessageRole.USER,
                content=[{"type": MessageType.IMAGE_URL.value, "image_url": {"url": image_url}}]
            ))

        return messages


if __name__ == "__main__":
    # uv run python -m siliconcrowds.prompt
    from rich import print as rich_print
    from siliconcrowds.context import Contextual, Context

    instruction = Instruction()
    print("================ Baseline Prompt: ==================")
    prompt: Prompt = instruction.get_baseline_prompt("baseline_instructional_1")
    rich_print(prompt)
    contextual = Contextual()
    ids: list[str] = contextual.get_ids()
    context: Context = contextual[ids[0]]

    messages: list[Message] = Instruction.build_message(prompt, context.prompt.transcript, context.prompt.image_url)
    print("================ Message: ==================")
    rich_print(messages)
