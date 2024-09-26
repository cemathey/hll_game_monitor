import enum

import pydantic


class CommandNames(enum.StrEnum):
    pass


class Payload(pydantic.BaseModel):
    """Used to add info to redis streams in a standardized format

    type: the class name of the encoded model
    payload: serialized model dump
    """

    type: str
    payload: str


class Message(pydantic.BaseModel):
    id: str | None = pydantic.Field(default=None)
