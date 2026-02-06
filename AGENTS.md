# SiliconCrowds Pilot

## Setup

### Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# or with Homebrew
brew install uv
```

### Create virtual environment and install dependencies

```bash
uv venv
source .venv/bin/activate
uv sync
```

### Environment variables

Copy `.env.example` to `.env` and add your Fireworks API key:

```bash
cp .env.example .env
```

```
FIREWORKS_API_KEY=your_api_key_here
```

## SDK Reference

Fireworks AI Python SDK: https://github.com/fw-ai-external/python-sdk

## Architecture

### siliconcrowds/model.py

A wrapper around the Fireworks SDK that provides type safe chat completions using Pydantic models.

**Enums:**
- `MessageRole`: Role of the message sender (USER, SYSTEM, ASSISTANT)
- `MessageType`: Content type (TEXT, IMAGE_URL)

**Pydantic Models:**
- `Config`: Model configuration with `temperature` (float, default 0.1). Note: Parameters must be supported by the specific model.
- `Message`: Chat message with `role` (MessageRole) and `content` (list of content dicts)
- `Usage`: Token usage stats (prompt_tokens, completion_tokens, total_tokens)
- `Response`: Complete response containing id, message, reasoning_content, model name, usage, and optional `structured_output` (BaseModel | None)

**Model Class:**
- `__init__(model: str, config: Config | None = None, retries: int = 2)`: Initializes with a model name, optional config, and retry count. Requires `FIREWORKS_API_KEY` environment variable.
- `invoke(messages: list[Message], structured_output: type[BaseModel] | None = None, retries: int | None = None) -> Response`: Sends messages to the Fireworks API and returns a typed response. When `structured_output` is provided, the API returns JSON matching the schema. If validation fails, the model automatically retries by sending the error back to the LLM for correction.

**Usage:**

```python
from siliconcrowds.model import Model, Config, Message, MessageRole, MessageType

# With default config (2 retries)
model = Model(model="accounts/fireworks/models/kimi-k2p5")

# With custom config and retries
model = Model(
    model="accounts/fireworks/models/kimi-k2p5",
    config=Config(temperature=0.5),
    retries=3
)

# Text message
response = model.invoke([
    Message(
        role=MessageRole.USER,
        content=[{"type": MessageType.TEXT.value, "text": "What is the capital of France?"}],
    )
])
print(response.message.content)

# Multimodal message (text + image)
response = model.invoke([
    Message(
        role=MessageRole.USER,
        content=[
            {"type": MessageType.TEXT.value, "text": "What's in this image?"},
            {"type": MessageType.IMAGE_URL.value, "image_url": {"url": "https://example.com/image.png"}},
        ],
    )
])

# Structured output with retry on validation failure
from siliconcrowds.schema import NumericSchema

response = model.invoke(
    [Message(role=MessageRole.USER, content=[{"type": MessageType.TEXT.value, "text": "What is 2 + 2?"}])],
    structured_output=NumericSchema,
    retries=2  # Optional: override instance default
)
print(response.structured_output.answer)  # 4
```

**Run directly:**

```bash
uv run python -m siliconcrowds.model
```

### siliconcrowds/schema.py

Pydantic models for structured output schemas used with the Model class.

**Pydantic Models:**
- `NumericSchema`: Schema for numeric answers with an `answer` field (int)
- `TimeSchema`: Schema for time answers in mm:ss format with validation

**Usage:**

```python
from siliconcrowds.schema import NumericSchema, TimeSchema
from siliconcrowds.model import Model, Message, MessageRole, MessageType

model = Model(model="accounts/fireworks/models/kimi-k2p5")

# Numeric response
response = model.invoke(
    [Message(role=MessageRole.USER, content=[{"type": MessageType.TEXT.value, "text": "How many planets are in our solar system?"}])],
    structured_output=NumericSchema
)
print(response.structured_output.answer)  # 8

# Time response
response = model.invoke(
    [Message(role=MessageRole.USER, content=[{"type": MessageType.TEXT.value, "text": "How long is a marathon in mm:ss?"}])],
    structured_output=TimeSchema
)
print(response.structured_output.answer)  # e.g., "126:00"
```

### siliconcrowds/prompt.py

Pydantic models for database entities with prompt generation capabilities, plus the `Instruction` class for managing prompts.

**Pydantic Models:**
- `Persona`: Represents a demographic persona with fields matching the `personas_representative` Supabase table
- `Prompt`: Represents a prompt template stored in the `prompts` table
- `Question`: Represents a question with image data from the `questions` table

**Persona Fields:**
- `id`: int
- `age_range`: str (e.g., "12-18", "19-29", "30-49", "50-66", "67+")
- `gender`: str (e.g., "Male", "Female")
- `ethnicity`: str (e.g., "a Norwegian background", "an Immigrant background")
- `education`: str (e.g., "Upper secondary", "Below upper secondary", "Higher education")
- `politics`: str (e.g., "Right-wing", "Left-wing", "Centrist")
- `weight`: float (sampling weight for representative surveys)

**Persona Methods:**
- `to_prompt() -> str`: Converts the persona to a natural language prompt for LLM role-playing

**Prompt Fields:**
- `id`: int
- `category`: str (e.g., "baseline", "generic_persona", "specific_persona")
- `system_prompt`: str
- `user_prompt`: str
- `template_name`: str
- `description`: str | None

**Question Fields:**
- `id`: int
- `question_id`: str
- `transcript`: str
- `image_path`: str (path to image in Supabase storage)
- `norways_answer`: str
- `actual_outcome`: str | None
- `air_date`: datetime | None
- `answer_type`: str | None

**Instruction Class:**
- `__init__()`: Loads all prompts from the database, organized by category into dictionaries keyed by `template_name`
- `get_baseline_prompt(prompt_name: str) -> Prompt`: Returns a baseline prompt by template name
- `get_generic_persona_prompt(prompt_name: str) -> Prompt`: Returns a generic persona prompt by template name
- `get_specific_persona_prompt(prompt_name: str) -> Prompt`: Returns a specific persona prompt by template name
- `build_message(prompt: Prompt, transcript: str, image_url: str | None = None) -> list[Message]`: Static method that constructs a list of Message objects from a prompt, transcript, and optional image URL. Handles system prompt, formatted user prompt, and image attachment.

**Usage:**

```python
from siliconcrowds.prompt import Persona, Prompt, Question, Instruction

persona = Persona(
    id=1,
    age_range="30-49",
    gender="Female",
    ethnicity="a Norwegian background",
    education="Higher education",
    politics="Centrist",
    weight=0.5
)
print(persona.to_prompt())
# "You are a Female aged 30-49 with a Norwegian background. Your education level is higher education. Your political views are Centrist."

# Using Instruction to get prompts and build messages
instruction = Instruction()
prompt = instruction.get_baseline_prompt("baseline_instructional_1")

# Build message list for LLM
from siliconcrowds.context import Contextual
contextual = Contextual()
context = contextual[contextual.get_ids()[0]]
messages = Instruction.build_message(prompt, context.prompt.transcript, context.prompt.image_url)
```

**Run directly:**

```bash
uv run python -m siliconcrowds.prompt
```

### siliconcrowds/bucket.py

Storage client for Supabase buckets with file listing and signed URL generation.

**Helper Functions:**
- `get_supabase_client() -> Client`: Creates and returns a Supabase client using `SUPABASE_URL` and `SUPABASE_KEY` environment variables. Shared by both `bucket.py` and `database.py`.

**Bucket Class:**
- `__init__(bucket_name: str)`: Initializes with a Supabase storage bucket name
- `list_files(path: str, sort_by: dict | None = None) -> list[dict]`: Lists files in the specified path. Default sort is by name descending.
- `list_public_urls(path: str, expires_in: int = 1800) -> dict[str, str]`: Returns a mapping of filename stems (without extensions) to signed URLs. URLs expire after `expires_in` seconds (default 30 minutes).

**Usage:**

```python
from siliconcrowds.bucket import Bucket

bucket = Bucket("pilot_images")

# List files in a path
files = bucket.list_files(path="pilot_images")

# Get signed URLs for all files in a path (keys are filename stems without extensions)
public_urls = bucket.list_public_urls(path="pilot_images", expires_in=600)
# {"q001": "https://...", "q002": "https://..."}
```

**Run directly:**

```bash
uv run python -m siliconcrowds.bucket
```

### siliconcrowds/database.py

Database client for Supabase with typed query methods.

**Database Class:**
- Initializes Supabase client using `get_supabase_client()` from `bucket.py`
- `get_personas(table_name: str = "personas_representative") -> list[Persona]`: Fetches all personas from the specified table
- `get_prompts_by_category(category: str, table_name: str = "prompts") -> dict[str, Prompt]`: Fetches prompts filtered by category, returns dict keyed by `template_name`
- `get_baseline_prompts(table_name: str = "prompts") -> dict[str, Prompt]`: Fetches prompts with category "baseline", returns dict keyed by `template_name`
- `get_generic_persona_prompts(table_name: str = "prompts") -> dict[str, Prompt]`: Fetches prompts with category "generic_persona", returns dict keyed by `template_name`
- `get_specific_persona_prompts(table_name: str = "prompts") -> dict[str, Prompt]`: Fetches prompts with category "specific_persona", returns dict keyed by `template_name`
- `get_questions(table_name: str = "questions") -> list[Question]`: Fetches all questions from the specified table

**Usage:**

```python
from siliconcrowds.database import Database
from siliconcrowds.prompt import Persona, Prompt, Question

db = Database()

# Fetch personas
personas: list[Persona] = db.get_personas()
system_prompt = personas[0].to_prompt()

# Fetch prompts by category (returns dict keyed by template_name)
baseline_prompts: dict[str, Prompt] = db.get_baseline_prompts()
generic_prompts: dict[str, Prompt] = db.get_generic_persona_prompts()
specific_prompts: dict[str, Prompt] = db.get_specific_persona_prompts()

# Access a specific prompt by template name
prompt = baseline_prompts["baseline_instructional_1"]

# Fetch questions
questions: list[Question] = db.get_questions()
```

**Run directly:**

```bash
uv run python -m siliconcrowds.database
```

### siliconcrowds/context.py

Aggregates questions from the database with their corresponding image URLs from storage into a unified context structure. This is the primary interface for accessing question data with images.

**Pydantic Models:**

- `ContextPrompt`: The prompt portion of a context
  - `transcript`: str (the question text)
  - `image_url`: str | None (signed URL to the question image)

- `Answer`: The answer portion of a context
  - `norways_answer`: str (Norway's collective answer)
  - `actual_outcome`: str | None (the actual outcome)
  - `answer_type`: str | None (type of answer expected)

- `Context`: Complete context for a single question
  - `id`: str (database ID)
  - `question_id`: str (unique question identifier)
  - `prompt`: ContextPrompt
  - `answer`: Answer

**Contextual Class:**

- `__init__(bucket_name: str = "pilot_images", path: str = "pilot_images")`: Loads all questions from the database and matches them with signed image URLs from the bucket. Contexts are indexed by `question_id`.
- `__len__() -> int`: Returns the number of contexts
- `__getitem__(question_id: str) -> Context`: Returns the context for the given question_id. Raises `KeyError` if not found.
- `get_ids() -> list[str]`: Returns all available question_ids

**Usage:**

```python
from siliconcrowds.context import Contextual, Context

# Load all contexts (fetches from database and generates signed URLs)
contextual = Contextual()

# Get all available question IDs
ids = contextual.get_ids()
print(f"Loaded {len(contextual)} contexts")

# Access a specific context by question_id
context: Context = contextual[ids[0]]

# Use the context data
print(context.prompt.transcript)  # Question text
print(context.prompt.image_url)   # Signed URL to image (or None)
print(context.answer.norways_answer)  # Norway's answer
```

**With Model Integration:**

```python
from siliconcrowds.context import Contextual
from siliconcrowds.model import Model, Message, MessageRole, MessageType

# Load contexts and model
contextual = Contextual()
model = Model(model="accounts/fireworks/models/kimi-k2p5")

# Get a context and build a multimodal message
context = contextual[contextual.get_ids()[0]]

content = [{"type": MessageType.TEXT.value, "text": context.prompt.transcript}]
if context.prompt.image_url:
    content.append({"type": MessageType.IMAGE_URL.value, "image_url": {"url": context.prompt.image_url}})

response = model.invoke([
    Message(role=MessageRole.USER, content=content)
])
print(response.message.content)
```

**Run directly:**

```bash
uv run python -m siliconcrowds.context
```

### Integration Example

Complete flow from database to LLM:

```python
from siliconcrowds.database import Database
from siliconcrowds.model import Model, Message, MessageRole, MessageType

# Fetch persona from database
db = Database()
persona = db.get_personas()[0]

# Create model and invoke with persona as system prompt
model = Model(model="accounts/fireworks/models/kimi-k2p5")
response = model.invoke([
    Message(
        role=MessageRole.SYSTEM,
        content=[{"type": MessageType.TEXT.value, "text": persona.to_prompt()}],
    ),
    Message(
        role=MessageRole.USER,
        content=[{"type": MessageType.TEXT.value, "text": "What do you think about climate policy?"}],
    ),
])
print(response.message.content)
```

### Multimodal Integration Example

Complete flow using `Instruction.build_message` to construct messages from prompts and contexts:

```python
from siliconcrowds.context import Contextual
from siliconcrowds.prompt import Instruction
from siliconcrowds.model import Model

# Load contexts and prompts
contextual = Contextual()
instruction = Instruction()

# Get context and prompt
context = contextual[contextual.get_ids()[0]]
prompt = instruction.get_baseline_prompt("baseline_instructional_1")

# Build messages using the static method
messages = Instruction.build_message(
    prompt,
    context.prompt.transcript,
    context.prompt.image_url
)

# Invoke model
model = Model(model="accounts/fireworks/models/kimi-k2p5")
response = model.invoke(messages)
print(response.message.content)
```
