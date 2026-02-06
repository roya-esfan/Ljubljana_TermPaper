from siliconcrowds.bucket import get_supabase_client
from siliconcrowds.prompt import Persona, Prompt, Question


class Database:
    def __init__(self) -> None:
        self.client = get_supabase_client()

    def get_personas(self, table_name: str = "personas_representative") -> list[Persona]:
        response = self.client.table(table_name).select("*").execute()
        return [Persona.model_validate(persona) for persona in response.data]

    def get_prompts_by_category(
        self, category: str, table_name: str = "prompts"
    ) -> dict[str, Prompt]:
        response = (
            self.client.table(table_name).select("*").eq("category", category).execute()
        )
        return {
            prompt["template_name"]: Prompt.model_validate(prompt)
            for prompt in response.data
        }

    def get_baseline_prompts(self, table_name: str = "prompts") -> dict[str, Prompt]:
        return self.get_prompts_by_category("baseline", table_name)

    def get_generic_persona_prompts(self, table_name: str = "prompts") -> dict[str, Prompt]:
        return self.get_prompts_by_category("generic_persona", table_name)

    def get_specific_persona_prompts(self, table_name: str = "prompts") -> dict[str, Prompt]:
        return self.get_prompts_by_category("specific_persona", table_name)

    def get_questions(self, table_name: str = "questions") -> list[Question]:
        response = self.client.table(table_name).select("*").execute()
        return [Question.model_validate(question) for question in response.data]


if __name__ == "__main__":
    # uv run python -m siliconcrowds.database
    from rich import print as rich_print

    database = Database()
    personas: list[Persona] = database.get_personas()
    print("================ Persona 1: ==================")
    rich_print(personas[0])
    rich_print(personas[0].to_prompt())

    baseline_prompts: dict[str, Prompt] = database.get_baseline_prompts()
    print("================ Baseline Prompts: ==================")
    for template_name, prompt in baseline_prompts.items():
        print(f"Template: {template_name}")
        rich_print(prompt)

    generic_persona_prompts: dict[str, Prompt] = database.get_generic_persona_prompts()
    print("================ Generic Persona Prompts: ==================")
    for template_name, prompt in list(generic_persona_prompts.items())[:1]:
        print(f"Template: {template_name}")
        rich_print(prompt)

    specific_persona_prompts: dict[str, Prompt] = database.get_specific_persona_prompts()
    print("================ Specific Persona Prompts: ==================")
    for template_name, prompt in list(specific_persona_prompts.items())[:1]:
        print(f"Template: {template_name}")
        rich_print(prompt)

    questions: list[Question] = database.get_questions()
    print("================ Question 1: ==================")
    rich_print(questions[0])