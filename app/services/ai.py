from openai import AsyncOpenAI

from app.config import Settings


class AIService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    def _instructions(self) -> str:
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

        parts.append(
            "You are talking privately with your owner in Telegram. "
            "Be natural, useful, and concise unless more detail is requested."
        )

        return "\n".join(parts)

    async def reply(
        self,
        history: list[dict],
        user_text: str,
    ) -> str:
        input_messages = [
            {"role": item["role"], "content": item["content"]}
            for item in history
        ]
        input_messages.append({"role": "user", "content": user_text})

        response = await self.client.responses.create(
            model=self.settings.openai_model,
            instructions=self._instructions(),
            input=input_messages,
            store=False,
        )

        answer = (response.output_text or "").strip()
        if not answer:
            return "I couldn't generate a text response. Please try again."

        return answer
