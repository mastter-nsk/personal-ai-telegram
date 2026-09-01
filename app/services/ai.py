import json
from collections.abc import Awaitable, Callable

from openai import AsyncOpenAI

from app.config import Settings


SaveMemoryCallback = Callable[[str], Awaitable[tuple[dict, bool]]]


class AIService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    def _instructions(self, memory_text: str) -> str:
        parts = [
            self.settings.personality.strip(),
            f"Your name is {self.settings.bot_name}.",
        ]

        if self.settings.owner_name.strip():
            parts.append(
                f"The owner's name is {self.settings.owner_name.strip()}."
            )

        if self.settings.interests.strip():
            parts.append(
                f"The owner's interests include: {self.settings.interests.strip()}."
            )

        parts.extend(
            [
                memory_text,
                (
                    "You are talking privately with your owner in Telegram. "
                    "Be natural, useful, and concise unless more detail is requested."
                ),
                (
                    "Use save_memory only for durable personal information that is "
                    "likely to be useful in future conversations: stable preferences, "
                    "interests, relationships, recurring habits, important long-term "
                    "plans, or explicit requests to remember something. "
                    "Do not save ordinary questions, temporary details, passwords, "
                    "API keys, authentication codes, financial credentials, or other secrets."
                ),
            ]
        )

        return "\n".join(parts)

    @staticmethod
    def _tools() -> list[dict]:
        return [
            {
                "type": "web_search",
                "search_context_size": "medium",
            },
            {
                "type": "function",
                "name": "save_memory",
                "description": (
                    "Save one concise, durable fact about the owner for use in future "
                    "conversations. Use only when the fact is likely to remain useful."
                ),
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "One concise standalone fact about the owner.",
                        }
                    },
                    "required": ["content"],
                    "additionalProperties": False,
                },
            },
        ]

    @staticmethod
    def _dump_output_item(item) -> dict:
        if hasattr(item, "model_dump"):
            return item.model_dump(exclude_none=True)
        return dict(item)

    async def transcribe_voice(self, audio_bytes: bytes) -> str:
        transcription = await self.client.audio.transcriptions.create(
            model=self.settings.transcription_model,
            file=("voice.ogg", audio_bytes, "audio/ogg"),
        )

        text = (transcription.text or "").strip()
        if not text:
            raise ValueError("Transcription returned empty text.")

        return text

    async def reply(
        self,
        history: list[dict],
        user_text: str,
        memory_text: str,
        save_memory: SaveMemoryCallback,
    ) -> str:
        conversation_input: list[dict] = [
            {"role": item["role"], "content": item["content"]}
            for item in history
        ]
        conversation_input.append({"role": "user", "content": user_text})

        response = await self.client.responses.create(
            model=self.settings.openai_model,
            instructions=self._instructions(memory_text),
            input=conversation_input,
            tools=self._tools(),
            tool_choice="auto",
            store=False,
        )

        for _ in range(3):
            function_calls = [
                item
                for item in response.output
                if getattr(item, "type", None) == "function_call"
                and getattr(item, "name", None) == "save_memory"
            ]

            if not function_calls:
                answer = (response.output_text or "").strip()
                if not answer:
                    return "I couldn't generate a text response. Please try again."
                return answer

            followup_input = list(conversation_input)
            followup_input.extend(
                self._dump_output_item(item) for item in response.output
            )

            for call in function_calls:
                try:
                    arguments = json.loads(call.arguments)
                    content = str(arguments.get("content", "")).strip()

                    if not content:
                        tool_result = {
                            "status": "error",
                            "message": "Memory content was empty.",
                        }
                    else:
                        memory, created = await save_memory(content)
                        tool_result = {
                            "status": "saved" if created else "already_exists",
                            "memory_id": memory["id"],
                        }
                except (json.JSONDecodeError, TypeError, ValueError) as exc:
                    tool_result = {
                        "status": "error",
                        "message": str(exc),
                    }

                followup_input.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": json.dumps(tool_result),
                    }
                )

            conversation_input = followup_input
            response = await self.client.responses.create(
                model=self.settings.openai_model,
                instructions=self._instructions(memory_text),
                input=conversation_input,
                tools=self._tools(),
                tool_choice="auto",
                store=False,
            )

        answer = (response.output_text or "").strip()
        if answer:
            return answer

        return "I couldn't complete that request. Please try again."
