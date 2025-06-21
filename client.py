import os
import sys
import json
import asyncio
from typing import Optional
from contextlib import AsyncExitStack
from dotenv import load_dotenv

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AzureOpenAI

load_dotenv()  # Load env variables

class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.azure_client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

    async def connect_to_server(self, server_script_path: str):
        """Connect to the MCP server (Python or Node script)"""
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.session.initialize()

        # List tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\n✅ Connected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """Use Azure OpenAI to process query and call tools via MCP"""
        messages = [{"role": "user", "content": query}]
        final_text = []

        response = await self.session.list_tools()
        available_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
            }
            for tool in response.tools
        ]

        # Initial LLM call
        response = self.azure_client.chat.completions.create(
            model=self.deployment,
            messages=messages,
            tools=available_tools,
            tool_choice="auto",
            max_tokens=1000
        )

        message = response.choices[0].message
        if message.content:
            final_text.append(message.content)

        # Tool call handling
        if message.tool_calls:
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                # Call the MCP tool
                tool_response = await self.session.call_tool(tool_name, tool_args)
                final_text.append(f"[Tool {tool_name} called with args {tool_args}]")
                final_text.append(str(tool_response))  # ✅ Show raw output in console

                # Add the tool call metadata to the conversation
                messages.append({
                    "role": "assistant",
                    "tool_calls": [tool_call.model_dump()]
                })

                # Add the actual tool response string (not result.content!)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(tool_response)  # ✅ Corrected here
                })

                # Ask Azure OpenAI to process tool output
                response = self.azure_client.chat.completions.create(
                    model=self.deployment,
                    messages=messages,
                    max_tokens=1000
                )
                follow_up = response.choices[0].message
                if follow_up.content:
                    final_text.append(follow_up.content)

        return "\n".join(final_text)

    async def chat_loop(self):
        """Interactive CLI chat"""
        print("\n🤖 MCP Client Started!")
        print("Type your query or 'quit' to exit.")
        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() == 'quit':
                    break
                response = await self.process_query(query)
                print("\n" + response)
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")

    async def cleanup(self):
        """Release resources"""
        await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
