from openai import OpenAI

from utils import settings

client = OpenAI(
    organization=settings.openai_org_id,
    project=settings.openai_project_id,
    api_key=settings.openai_api_key
)