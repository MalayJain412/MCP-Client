import asyncio
from asyncio.log import logger
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import ToolMessage
import config
from servers import SERVERS

async def main():
    """
    ---------------------------------------------------------
    Initialize MCP Client and Retrieve Available Tools
    ---------------------------------------------------------

    MultiServerMCPClient connects to one or more MCP servers defined
    in the SERVERS configuration. MCP (Model Context Protocol) servers
    expose tools that an LLM can call during reasoning.

    Example tools might include:
        - mathematical operations (add, multiply)
        - database queries
        - API integrations
        - retrieval/search utilities

    `client.get_tools()` asynchronously fetches all tools exposed by
    those servers and returns them as LangChain tool objects.

    We then convert the list of tools into a dictionary:

        { tool_name : tool_object }

    This allows constant-time lookup when the LLM later asks
    to execute a tool by name.
    """

    client = MultiServerMCPClient(SERVERS) # Initialize the client with the server configurations
    tools = await client.get_tools() # Retrieve the tools from the servers
    
    named_tools ={}
    for tool in tools:
        named_tools[tool.name] = tool
    # print(named_tools)
    print("Available tools:", named_tools.keys())
    

    """
    ---------------------------------------------------------
    Initialize Azure OpenAI LLM
    ---------------------------------------------------------

    AzureChatOpenAI is the LangChain wrapper around Azure-hosted
    OpenAI models.

    Required parameters include:
        openai_api_version  -> API version used by Azure OpenAI
        azure_deployment    -> the deployment name in Azure
        azure_endpoint      -> Azure OpenAI endpoint URL
        api_key             -> authentication key
        temperature         -> randomness control (0 = deterministic)

    The LLM will later be augmented with tools so it can
    decide when to call external functions instead of
    answering directly.
    """

    # logger.info("Initializing Azure OpenAI LLM")
    print("Initializing Azure OpenAI LLM")
    llm = AzureChatOpenAI(
        openai_api_version = config.AZURE_API_VERSION,
        azure_deployment = config.AZURE_DEPLOYMENT,
        azure_endpoint = config.AZURE_OPENAI_ENDPOINT,
        api_key = config.AZURE_OPENAI_API_KEY,
        temperature = 0
    )
    # logger.info("LLM initialized successfully")
    print("LLM initialized successfully")
    

    """
    ---------------------------------------------------------
    Bind Tools to the LLM
    ---------------------------------------------------------

    `bind_tools()` informs the LLM about the available tools.

    Once bound, the model can decide during inference whether
    to call a tool. Instead of generating a final answer,
    the LLM may return structured `tool_calls` such as:

        {
            "name": "add",
            "args": {"a":5, "b":3},
            "id": "call_xyz"
        }

    The program must then execute the tool and return
    the results back to the LLM.
    """

    llm_with_tools = llm.bind_tools(tools)
    

    """
    ---------------------------------------------------------
    Send Test Prompt to the LLM
    ---------------------------------------------------------

    This prompt intentionally requires tool usage so the model
    will generate tool calls instead of computing internally.

    The prompt asks for:
        1. addition of 5 and 3
        2. multiplication of 5 and 3
    """

    # test_prompt = "What is the result of adding 5 and 3? And multiplication of 5 and 3?"
    # test_prompt = "What is the capital of India"
    # test_prompt = "Please summarize my expanses of feburary 2026"
    test_prompt = "Roll 5 dices"
    # logger.info(f"Sending test prompt to LLM: {test_prompt}")
    print(f"Sending user prompt to LLM:\n ########## \n {test_prompt} \n ########## \n")
    
    """
    ---------------------------------------------------------
    First LLM Call (Tool Planning Stage)
    ---------------------------------------------------------

    At this stage the LLM examines the prompt and decides
    which tools should be executed.

    Instead of a normal answer, the response contains:

        response.tool_calls

    Each tool call includes:
        - name : tool to execute
        - args : arguments for the tool
        - id   : unique identifier for the tool request

    The tool_call_id is important because it allows the LLM
    to match results back to the correct tool invocation.
    """
    response = await llm_with_tools.ainvoke(test_prompt)
    # print(f"Response from LLM: {response}")
    
    """
    In case the user prompt do not need to call of the tools, then we directly print the content.
    """
    if not getattr(response,"tool_calls",None):
        print("\nLLM Reply::\n ########## \n", response.content," \n ########## \n")
        return
        
        
    print("Selecting the tools")

    # selected_tool = response.tool_calls[0]["name"]
    # selected_tool_args = response.tool_calls[0]["args"]
    
    selected_tools = []
    selected_tools_args = []
    for tool in response.tool_calls:
        selected_tools.append(tool['name'])
        selected_tools_args.append(tool['args'])
        
    print(f"tools: {selected_tools}, args: {selected_tools_args}")


    """
    ---------------------------------------------------------
    Execute Tools Requested by the LLM
    ---------------------------------------------------------

    For each tool call returned by the model:
        1. Extract tool name
        2. Extract arguments
        3. Execute the tool asynchronously
        4. Extract the result value
        5. Wrap the result inside a ToolMessage

    MCP tool outputs are returned in a structured format:

        [
            {
                "type": "text",
                "text": "8.0"
            }
        ]

    The actual value is therefore accessed using:

        result[0]["text"]

    The result is wrapped in a ToolMessage so it can be
    sent back to the LLM along with the original tool_call_id.
    """

    tool_result = []
    # for tool in selected_tools:
    #     args = selected_tools_args[selected_tools.index(tool)]
    #     result = await named_tools[tool].ainvoke(args)
    #     value = result[0]["text"]
    #     tool_result.append(value)
    
    for tool in response.tool_calls:
        tool_name = tool["name"]
        tool_args = tool['args']
        tool_call_id = tool['id']
        result = await named_tools[tool_name].ainvoke(tool_args)
        # print(result)
        values = result[0]["text"]
        # print (f"Result from tool '{tool_name}' with arguments {tool_args}: {values}")
        
        tool_result.append(
            ToolMessage(content = values,
                        tool_call_id = tool_call_id,
                        tool_name = tool_name
                        )
        )
        
    # print(tool_result)
    for result in tool_result:
        print(f"Result from tool: {result}")  


    """
    ---------------------------------------------------------
    Send Tool Results Back to the LLM
    ---------------------------------------------------------

    After executing tools, the results must be returned to
    the model so it can generate the final answer.

    The conversation history passed to the model includes:

        1. original user prompt
        2. AI message containing tool_calls
        3. ToolMessage responses with tool outputs

    The `*tool_result` syntax unpacks the list so each
    ToolMessage becomes an individual message.

    Without unpacking:

        [test_prompt, response, tool_result]

    This would produce nested lists.

    With unpacking:

        [test_prompt, response, *tool_result]

    Python expands the structure into:

        [
            test_prompt,
            response,
            ToolMessage(...),
            ToolMessage(...)
        ]

    LangChain expects each message to appear individually
    in the conversation history.
    """

    # tool_message = ToolMessage(content = tool_result, tool_name = selected_tools)
    print("Invoking the tool calls")
    final_response = await llm_with_tools.ainvoke([test_prompt, response, *tool_result])
    
    # print(final_response.content)
    
    llm_reply = final_response.content
    
    print(f"\nFinal response from LLM:\n ########## \n {llm_reply}\n ########## \n")    
    
if __name__ == "__main__":
    asyncio.run(main())