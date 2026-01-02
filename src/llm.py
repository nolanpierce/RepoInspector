from openai import OpenAI
from config import vultr_model, vultr_base, vultr_token

client: OpenAI = OpenAI(api_key=vultr_token, base_url=vultr_base)