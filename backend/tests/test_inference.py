from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from typing import Literal

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

load_dotenv()
ProviderName = Literal["modal-standard", "modal-turbo", "deepseek"]


@dataclass(frozen=True)
class ProviderConfig:
    model: str
    base_url: str
    api_key: str
    timeout: float = 720.0
    append_v1: bool = False
    reasoning_effort: str | None = None
    extra_body: dict | None = None


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _modal_base_url(name: str) -> str:
    raw_url = _require_env(name).rstrip("/")
    return raw_url if raw_url.endswith("/v1") else f"{raw_url}/v1"


def get_provider_config(provider: ProviderName, enable_deepseek_thinking: bool) -> ProviderConfig:
    if provider == "modal-standard":
        return ProviderConfig(
            model=os.getenv("MODAL_MODEL", "google/gemma-4-26B-A4B-it"),
            base_url=_modal_base_url("MODAL_STANDARD_BASE_URL"),
            api_key=os.getenv("MODAL_API_KEY", "unused"),
        )

    if provider == "modal-turbo":
        return ProviderConfig(
            model=os.getenv("MODAL_MODEL", "google/gemma-4-26B-A4B-it"),
            base_url=_modal_base_url("MODAL_TURBO_BASE_URL"),
            api_key=os.getenv("MODAL_API_KEY", "unused"),
        )

    extra_body = {"thinking": {"type": "enabled"}} if enable_deepseek_thinking else None
    return ProviderConfig(
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"),
        api_key=_require_env("DEEPSEEK_API_KEY"),
        timeout=180.0,
        reasoning_effort="high" if enable_deepseek_thinking else None,
        extra_body=extra_body,
    )


def get_llm(provider: ProviderName, enable_deepseek_thinking: bool = False) -> ChatOpenAI:
    config = get_provider_config(provider, enable_deepseek_thinking)
    return ChatOpenAI(
        model=config.model,
        base_url=config.base_url,
        api_key=config.api_key,
        temperature=0,
        timeout=config.timeout,
        max_retries=1,
        reasoning_effort=config.reasoning_effort,
        extra_body=config.extra_body,
    )


def ask_once(llm: ChatOpenAI, message: str) -> str:
    response = llm.invoke(
        [
            SystemMessage(
                content=(
                    "You are OllyUW's model smoke-test assistant. "
                    "Answer concisely and mention which capability you are testing."
                )
            ),
            HumanMessage(content=message),
        ]
    )
    return str(response.content)


def chat_loop(llm: ChatOpenAI) -> None:
    print("Type 'exit' to stop.")
    while True:
        message = input("\nuser> ").strip()
        if message.lower() in {"exit", "quit"}:
            return
        if not message:
            continue
        print(f"\nassistant> {ask_once(llm, message)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test LangChain inference providers.")
    parser.add_argument(
        "--provider",
        choices=["modal-standard", "modal-turbo", "deepseek"],
        default=os.getenv("OLLYUW_PROVIDER", "deepseek"),
    )
    parser.add_argument(
        "--message",
        default="In one paragraph, explain why citation grounding matters for underwriting.",
    )
    parser.add_argument("--chat", action="store_true", help="Start a simple terminal chat loop.")
    parser.add_argument(
        "--deepseek-thinking",
        action="store_true",
        help="Enable DeepSeek thinking mode and high reasoning effort.",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    try:
        llm = get_llm(args.provider, enable_deepseek_thinking=args.deepseek_thinking)
    except RuntimeError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    if args.chat:
        chat_loop(llm)
        return

    print(ask_once(llm, args.message))


if __name__ == "__main__":
    main()