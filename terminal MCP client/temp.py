import asyncio
from asyncio.log import logger
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import AzureChatOpenAI
import config
from servers import SERVERS

async def main():
    # ---------------------------------------------------------
    # Initialize the MultiServerMCPClient and retrieve tools
    # ---------------------------------------------------------
    client = MultiServerMCPClient(SERVERS) # Initialize the client with the server configurations
    tools = await client.get_tools() # Retrieve the tools from the servers
    
    named_tools ={}
    for tool in tools:
        named_tools[tool.name] = tool
    # print(named_tools)
    
    # ---------------------------------------------------------
    # AzureOpenAI LLm
    # ---------------------------------------------------------
    logger.info("Initializing Azure OpenAI LLM")
    llm = AzureChatOpenAI(
        openai_api_version = config.AZURE_API_VERSION,
        azure_deployment = config.AZURE_DEPLOYMENT,
        azure_endpoint = config.AZURE_OPENAI_ENDPOINT,
        api_key = config.AZURE_OPENAI_API_KEY,
        temperature = 0
    )
    logger.info("LLM initialized successfully")
    
    # ---------------------------------------------------------
    # Adding tools to the LLM
    # ---------------------------------------------------------
    llm_with_tools = llm.bind_tools(tools)
    
    # ---------------------------------------------------------
    # Test prompt to the LLM
    # ---------------------------------------------------------
    test_prompt = "What is the result of adding 5 and 3, and then multiplying the result by 2?"
    logger.info(f"Sending test prompt to LLM: {test_prompt}")
    
    # ---------------------------------------------------------
    # Get response from the LLM (This will return the tools to use)
    # ---------------------------------------------------------
    response = await llm_with_tools.ainvoke(test_prompt)
    print(f"Response from LLM: {response}")
    
    # for tool in response.tool_calls:
    #     print(f"Tool used: {tool.name}, Arguments: {tool.arguments}, Result: {tool.result}")
    
    for tool in response.tool_calls:
        print(f"\nTool used: {tool['name']}, Arguments: {tool['args']}\n")
        
    # ---------------------------------------------------------
    # Invoking the tools and getting results
    # ---------------------------------------------------------
    for tool in response.tool_calls:
        tool_name = tool['name']
        tool_args = tool['args']
        
        if tool_name in named_tools:
            logger.info(f"Invoking tool: {tool_name} with arguments: {tool_args}")
            result = await named_tools[tool_name].ainvoke(**tool_args)
            logger.info(f"Result from tool '{tool_name}': {result}")
        else:
            logger.warning(f"Tool '{tool_name}' not found in the retrieved tools")


    
if __name__ == "__main__":
    asyncio.run(main())