from pydantic import BaseModel, Field


class NumericSchema(BaseModel):
    answer: int = Field(
        description=(
            "Integer numeric answer only (e.g., '13', '1242'). "
            "Return the raw integer with no units or explanatory text. "
            "Use for questions that are NOT about time duration. "
            "Examples of numeric questions: "
            "'How many tries does it take?', "
            "'How many goals will they score within 60 seconds?', "
            "'How many dogs will run from A to B?'"
        )
    )


class TimeSchema(BaseModel):
    answer: str = Field(
        pattern=r'^\d{1,2}:[0-5]\d$',
        description=(
            "Time duration in mm:ss format (e.g., '00:48', '29:57'). "
            "mm:ss corresponds to minutes:seconds. "
            "Only use for questions asking how long something takes or how much time passes. "
            "Examples of time questions: "
            "'How long will it take to accomplish the task?', "
            "'How much time does it take to go from A to B?'"
        )
    )