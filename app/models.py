from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Kind = Literal["movie", "anime"]
Status = Literal["planned", "watching", "completed", "dropped"]
EditableStatus = Literal["planned", "watching", "dropped"]


class UserInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    username: str = Field(min_length=1, max_length=50, examples=["nikko"])


class User(UserInput):
    id: int
    created_at: str


class TitleInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=150, examples=["Steins;Gate"])
    kind: Kind = Field(examples=["anime"])
    total_episodes: int = Field(default=1, ge=1, le=5000, examples=[24])

    @model_validator(mode="after")
    def movies_have_one_part(self):
        if self.kind == "movie" and self.total_episodes != 1:
            raise ValueError("A movie must have total_episodes = 1")
        return self


class Title(TitleInput):
    id: int


class EntryInput(BaseModel):
    user_id: int = Field(ge=1, examples=[1])
    title_id: int = Field(ge=1, examples=[1])


class EntryUpdate(BaseModel):
    status: EditableStatus = Field(examples=["watching"])
    rating: int = Field(default=0, ge=0, le=10, examples=[8])


class Entry(BaseModel):
    id: int
    user_id: int
    username: str
    title_id: int
    title_name: str
    kind: Kind
    total_episodes: int
    status: Status
    episodes_watched: int
    rating: int


class ProgressInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    episodes: int = Field(ge=1, le=5000, examples=[3])
    note: str = Field(default="", max_length=200, examples=["Watched after class"])


class FinishInput(BaseModel):
    rating: int = Field(default=0, ge=0, le=10, examples=[9])


class HistoryRecord(BaseModel):
    id: int
    entry_id: int
    episodes_added: int
    note: str
    logged_at: str
