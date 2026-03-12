import logging
import sys

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import ToolMessage

import config
from servers import SERVERS


# -------------------------------
# Logging Setup (works with uvicorn)
# -------------------------------

logger = logging.getLogger("mcp-agent")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

handler.setFormatter(formatter)

if not logger.handlers:
    logger.addHandler(handler)


# -------------------------------
# Agent Class
# -------------------------------

class MCPAgent:

    def __init__(self):

        self.client = None
        self.tools = None
        self.named_tools = None
        self.llm = None
        self.llm_with_tools = None


    async def initialize(self):
        """Initialize MCP client, tools and LLM once at startup"""

        logger.info("Initializing MCP client")

        self.client = MultiServerMCPClient(SERVERS)

        logger.info("Fetching tools from MCP servers")

        self.tools = await self.client.get_tools()

        self.named_tools = {tool.name: tool for tool in self.tools}

        logger.info("Available tools: %s", list(self.named_tools.keys()))

        logger.info("Initializing Azure OpenAI LLM")

        self.llm = AzureChatOpenAI(
            openai_api_version=config.AZURE_API_VERSION,
            azure_deployment=config.AZURE_DEPLOYMENT,
            azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
            api_key=config.AZURE_OPENAI_API_KEY,
            temperature=0
        )

        self.llm_with_tools = self.llm.bind_tools(self.tools)

        logger.info("MCP Agent initialized successfully")


    async def run(self, prompt: str):

        logger.info("User prompt: %s", prompt)

        response = await self.llm_with_tools.ainvoke(prompt)

        logger.info("LLM initial response received")

        if not getattr(response, "tool_calls", None):

            logger.info("No tool calls needed")
            return response.content


        logger.info("LLM requested tool calls: %s", response.tool_calls)

        tool_messages = []

        for tool in response.tool_calls:

            tool_name = tool["name"]
            tool_args = tool["args"]
            tool_call_id = tool["id"]

            logger.info(
                "Executing tool: %s | args: %s",
                tool_name,
                tool_args
            )

            result = await self.named_tools[tool_name].ainvoke(tool_args)

            logger.info("Raw tool result: %s", result)

            value = "Tool returned no result"

            if result:

                if isinstance(result, list):

                    if len(result) > 0 and isinstance(result[0], dict):

                        if "text" in result[0]:
                            value = result[0]["text"]
                        else:
                            value = str(result[0])

                    else:
                        value = str(result)

                else:
                    value = str(result)

            logger.info("Parsed tool output: %s", value)

            tool_messages.append(
                ToolMessage(
                    content=value,
                    tool_call_id=tool_call_id,
                    tool_name=tool_name
                )
            )


        logger.info("Sending tool outputs back to LLM")

        final = await self.llm_with_tools.ainvoke(
            [prompt, response, *tool_messages]
        )

        logger.info("Final response: %s", final.content)

        return final.content