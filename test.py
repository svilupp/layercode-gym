from pydantic import BaseModel

from pydantic_ai import Agent


class CityLocation(BaseModel):
    city: str
    country: str


agent = Agent('openai:gpt-4.1-nano', output_type=CityLocation)
result = agent.run_sync('Where were the olympics held in 2012?')
print(result.all_messages())
#> city='London' country='United Kingdom'