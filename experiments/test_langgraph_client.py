from typing import Any

from langchain_core.messages import HumanMessage
from langgraph_sdk.client import get_client
from langgraph_sdk.schema import Run, Thread

url_for_cli_deployment = "http://localhost:8123"
client = get_client(url=url_for_cli_deployment)


async def get_thread_id():
    return await client.threads.create()


async def get_runs(thread: Thread):
    return await client.runs.list(thread["thread_id"])


async def get_run_details(thread: Thread, run: Run):
    return await client.runs.get(thread["thread_id"], run["run_id"])


async def stream_agent(thread: Thread, agent_name: str, input: dict[str, Any]):
    async for chunk in client.runs.stream(thread["thread_id"], agent_name, input=input, stream_mode=["updates"]):
        print(f"-----{chunk.event}-----")
        print(chunk.data)

    print(type(chunk))
    return chunk


async def main():
    thread = await get_thread_id()
    print(thread)
    runs = await get_runs(thread)

    if runs:
        print(runs)
        return

    user_input = "pizza et ananas les gens qui mangent ça sont trop bizarre"
    graph_name = "joker"
    # run: Run = await client.runs.create(thread["thread_id"], graph_name, input={"messages": [HumanMessage(user_input)]})
    run = await stream_agent(thread, graph_name, {"messages": [HumanMessage(user_input)]})
    print(run)
    # run_details = await get_run_details(thread, run)
    # # print(run_details)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
