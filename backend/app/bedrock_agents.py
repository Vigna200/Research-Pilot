"""Optional AWS Bedrock Agent bridge, intentionally inactive without configuration."""
from uuid import uuid4
from .config import settings

class BedrockAgentUnavailable(RuntimeError): pass

def configured() -> bool:
    return bool(settings.bedrock_agent_id and settings.bedrock_agent_alias_id)

def invoke_research_planner(question: str) -> str:
    """Invoke a Bedrock Agent. AWS credentials/permissions are supplied by the runtime.

    The Bedrock agent should be configured with constrained tools/action groups for
    planning only; scholarly-source evidence remains retrieved by this application.
    """
    if not configured():
        raise BedrockAgentUnavailable("Bedrock Agent ID and alias are not configured")
    try:
        import boto3
        client = boto3.client("bedrock-agent-runtime", region_name=settings.aws_region)
        response = client.invoke_agent(
            agentId=settings.bedrock_agent_id,
            agentAliasId=settings.bedrock_agent_alias_id,
            sessionId=str(uuid4()),
            inputText=("Create a concise scholarly search plan for this question. Do not claim facts or invent papers. " + question),
            enableTrace=True,
        )
        completion = response.get("completion")
        if not completion: raise BedrockAgentUnavailable("Bedrock Agent returned no completion stream")
        return "".join(event["chunk"]["bytes"].decode("utf-8") for event in completion if "chunk" in event)
    except ImportError as error:
        raise BedrockAgentUnavailable("boto3 is not installed") from error
    except Exception as error:
        raise BedrockAgentUnavailable(f"Bedrock Agent invocation failed: {error}") from error
