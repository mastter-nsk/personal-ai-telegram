from app.db import Database


class MemoryService:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def list(self, user_id: int) -> list[dict]:
        return await self.db.list_memories(user_id=user_id)

    async def add_manual(self, user_id: int, content: str) -> tuple[dict, bool]:
        return await self.db.add_memory(
            user_id=user_id,
            content=content,
            source="manual",
        )

    async def add_auto(self, user_id: int, content: str) -> tuple[dict, bool]:
        return await self.db.add_memory(
            user_id=user_id,
            content=content,
            source="auto",
        )

    async def delete(self, user_id: int, memory_id: int) -> bool:
        return await self.db.delete_memory(
            user_id=user_id,
            memory_id=memory_id,
        )

    @staticmethod
    def format_for_prompt(memories: list[dict]) -> str:
        if not memories:
            return "No long-term memories have been saved yet."

        lines = [f"- {item['content']}" for item in memories]
        return "Long-term memories about the owner:\n" + "\n".join(lines)
