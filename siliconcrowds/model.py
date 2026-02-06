import os
from enum import Enum
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

load_dotenv()

from fireworks import Fireworks  # noqa: E402

class Config(BaseModel):
    temperature: float = Field(default=0.1)


class MessageRole(str, Enum):
    USER = "user"
    SYSTEM = "system"
    ASSISTANT = "assistant"


class MessageType(str, Enum):
    TEXT = "text"
    IMAGE_URL = "image_url"


class Message(BaseModel):
    role: MessageRole
    content: list[dict[str, Any]]


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class Response(BaseModel):
    id: str
    message: Message
    reasoning_content: str | None = None
    model: str
    usage: Usage
    structured_output: BaseModel | None = None


class Model:
    def __init__(self, model: str, config: Config | None = None, retries: int = 2) -> None:
        api_key: str | None = os.environ.get("FIREWORKS_API_KEY")
        if not api_key:
            raise ValueError("FIREWORKS_API_KEY is not set")
        self.model = model
        self.config = config or Config()
        self.retries = retries
        self.client = Fireworks(api_key=api_key)

    def _build_response(
        self,
        response: Any,
        choice: Any,
        content: list[dict[str, Any]],
        parsed_output: BaseModel | None = None,
    ) -> Response:
        return Response(
            id=response.id,
            message=Message(role=MessageRole(choice.role), content=content),
            reasoning_content=choice.reasoning_content,
            model=response.model,
            usage=Usage.model_validate(vars(response.usage)),
            structured_output=parsed_output,
        )

    def invoke(
        self,
        messages: list[Message],
        structured_output: type[BaseModel] | None = None,
        retries: int | None = None,
    ) -> Response:
        retries = retries if retries is not None else self.retries
        current_messages = list(messages)

        for attempt in range(retries):
            params: dict[str, Any] = {
                "model": self.model,
                "messages": [msg.model_dump() for msg in current_messages],
            }
            if structured_output:
                params["response_format"] = {
                    "type": "json_object",
                    "schema": structured_output.model_json_schema(),
                }
            params.update(self.config.model_dump())

            response = self.client.chat.completions.create(**params)
            choice = response.choices[0].message
            content = choice.content
            if isinstance(content, str):
                content = [{"type": MessageType.TEXT.value, "text": content}]

            if not structured_output:
                return self._build_response(response, choice, content)

            try:
                parsed = structured_output.model_validate_json(content[0]["text"])
                return self._build_response(response, choice, content, parsed)
            except ValidationError as e:
                if attempt < retries - 1:
                    correction = (
                        f"Your previous response had a validation error: {e}. "
                        "Please correct your response to match the required format."
                    )
                    current_messages.append(
                        Message(role=MessageRole.ASSISTANT, content=content)
                    )
                    current_messages.append(
                        Message(
                            role=MessageRole.USER,
                            content=[{"type": MessageType.TEXT.value, "text": correction}],
                        )
                    )
                    continue
                raise

        raise RuntimeError("Retry loop completed without returning a response")


if __name__ == "__main__":
    # uv run python -m siliconcrowds.model
    from rich import print as rich_print
    from siliconcrowds.bucket import Bucket
    
    model = Model(model="accounts/fireworks/models/qwen3-vl-30b-a3b-thinking")

    print("================ Text Response: ==================")
    text_response = model.invoke(
        [
            Message(
                role=MessageRole.USER,
                content=[
                    {
                        "type": MessageType.TEXT.value,
                        "text": "What is the capital of France?",
                    }
                ],
            )
        ]
    )
    rich_print(text_response)

    print("================ Image Response: ==================")
    image_response = model.invoke(
        [
            Message(
                role=MessageRole.USER,
                content=[
                    {"type": MessageType.TEXT.value, "text": "What's in this image?"},
                    {
                        "type": MessageType.IMAGE_URL.value,
                        "image_url": {
                            "url": "https://storage.googleapis.com/fireworks-public/image_assets/fireworks-ai-wordmark-color-dark.png"
                        },
                    },
                ],
            )
        ]
    )
    rich_print(image_response)

    print("================ Public URLs: ==================")
    bucket = Bucket("pilot_images")
    public_urls: dict[str, str] = bucket.list_public_urls(path="pilot_images")
    filename, public_url = next(iter(public_urls.items()))
    rich_print(f"Filename: {filename} | Public URL: {public_url}")
    image_response = model.invoke(
        [
            Message(
                role=MessageRole.USER,
                content=[
                    {"type": MessageType.TEXT.value, "text": "What's in this image?"},
                    {
                        "type": MessageType.IMAGE_URL.value,
                        "image_url": {
                            "url": public_url
                        },
                    },
                ],
            )
        ]
    )
    rich_print(image_response)