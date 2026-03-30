import asyncio
import os

import chainlit as cl
from dotenv import load_dotenv

from sql_agent.agent import build_agent_runtime
from sql_agent.config import load_settings

load_dotenv(override=True)

# Chainlit reserves DATABASE_URL for its own Postgres data layer. We use
# APP_DATABASE_URL for the SQL agent runtime to avoid DSN collisions.
if os.getenv("DATABASE_URL") and not os.getenv("APP_DATABASE_URL"):
    os.environ["APP_DATABASE_URL"] = os.getenv("DATABASE_URL", "")
os.environ.pop("DATABASE_URL", None)


@cl.on_chat_start
async def on_chat_start() -> None:
    try:
        settings = load_settings()
        runtime = await asyncio.to_thread(build_agent_runtime, settings)
        cl.user_session.set("runtime", runtime)
        cl.user_session.set("init_error", None)
    except Exception as exc:  # noqa: BLE001
        cl.user_session.set("runtime", None)
        cl.user_session.set("init_error", str(exc))
        await cl.Message(
            content=(
                "Initialization failed. Check environment variables and connectivity.\n"
                f"Error: {exc}"
            )
        ).send()
        return

    await cl.Message(
        content=(
            "Text-to-SQL assistant is ready. "
            "Ask a question in natural language and I will generate SQL over your allowlisted database tables."
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    runtime = cl.user_session.get("runtime")
    if runtime is None:
        init_error = cl.user_session.get("init_error")
        if init_error:
            await cl.Message(
                content=(
                    "Agent is not initialized due to startup error:\n"
                    f"{init_error}"
                )
            ).send()
        else:
            await cl.Message(content="Agent is not initialized. Restart the chat after fixing configuration.").send()
        return

    response = await asyncio.to_thread(runtime.run, message.content)
    await cl.Message(content=response).send()
