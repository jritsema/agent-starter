import requests
import uuid

prompt = "What's the latest hot thing in tech?"

response = requests.post(
    "http://localhost:8080/invocations",
    json={"input": {"prompt": prompt, "user_id": "123"}},
    stream=True,
    headers={
        "Accept": "text/event-stream",
        "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": str(uuid.uuid4()),
    }
)

for line in response.iter_lines(decode_unicode=True):
    if line and line.startswith("data: "):
        print(line[6:], end="", flush=True)
print()
