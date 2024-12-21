import tomli
from pathlib import Path
# from pydantic_settings import BaseSettings, SettingsConfigDict, TomlConfigSettingsSource
from pydantic import BaseModel
from typing import Optional, Dict, List

path = Path(__file__).parent


class GigaSettings(BaseModel):
    base_url: str
    cert_file: str
    key_file: str
    model: str
    verify_ssl_certs: bool
    profanity_check: bool
    streaming: bool
    timeout: int


class InvokeParametrs(BaseModel):
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    repetition_penalty: Optional[float] = None
    max_tokens: Optional[int] = None


class Instruction(BaseModel):
    text: Optional[str] = None
    name: Optional[str] = None


class Instructions(BaseModel):
    progress: Optional[Instruction] = None
    education: Optional[Instruction] = None
    childcare: Optional[Instruction] = None
    benefits: Optional[Instruction] = None
    vacation: Optional[Instruction] = None
    chtodelat: Optional[Instruction] = None
    checklist: Optional[Instruction] = None


class Prompts(BaseModel):
    system_prompt_template: Optional[str] = None
    user_prompt_template: Optional[str] = None
    instructions: Optional[Instructions] = None
    examples: Optional[List] = None


class ParametrsAndPromts(BaseModel):
    logfile: str
    parametrs: Optional[InvokeParametrs] = None
    prompts: Optional[Prompts] = None
