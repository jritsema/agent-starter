import json
import boto3
import os
from datetime import datetime, timezone

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])

def lambda_handler(event, context):
    tool_name = context.client_context.custom["bedrockAgentCoreToolName"]
    print(f"Tool name: {tool_name}")

    if "put_records" in tool_name:
        return put_record(event)

    elif "get_records" in tool_name:
        return get_records(event)

    else:
        return {"error": f"Unknown tool: {tool_name}"}

def put_record(event):
    try:
        records = event["records"]
        created_at = datetime.now(timezone.utc).isoformat()

        with table.batch_writer() as batch:
            for record in records:
                item = {
                    "id": f"{record['date']}#{record['topic']}",
                    "date": record["date"],
                    "topic": record["topic"],
                    "ranking": int(record["ranking"]),
                    "description": record["description"],
                    "created_at": created_at
                }
                batch.put_item(Item=item)

        return {"result": f"Successfully added {len(records)} records"}

    except Exception as e:
        return {"error": str(e)}

def get_records(event):
    try:
        response = table.scan()
        items = response.get("Items", [])
        return {"result": json.dumps(items, default=str)}

    except Exception as e:
        return {"error": str(e)}
