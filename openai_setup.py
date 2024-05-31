from openai import OpenAI

from utils import settings

client = OpenAI(
    organization=settings.openai_org_id,
    project=settings.openai_project_id,
    api_key=settings.openai_api_key
)


def askOpenAI(system, user, json=False):
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        response_format={"type": "json_object" if json else "text"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]
    )
    return completion.choices[0].message.content
