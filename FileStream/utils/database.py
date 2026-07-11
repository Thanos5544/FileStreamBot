import motor.motor_asyncio
import datetime
from typing import Dict, List


class Database:
    def __init__(self, uri: str, database_name: str):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db["users"]
        self.file = self.db["files"]

    # ---------------- USER ---------------- #
    async def add_user(self, user_id: int):
        await self.col.update_one(
            {"id": user_id},
            {"$set": {"id": user_id, "type": "user"}},
            upsert=True
        )

    async def delete_user(self, user_id: int):
        await self.col.delete_one({"id": user_id})

    async def get_user(self, user_id: int):
        return await self.col.find_one({"id": user_id})

    async def get_all_users(self):
        return self.col.find({})

    async def total_users_count(self):
        return await self.col.count_documents({"type": "user"})

    async def is_user_banned(self, user_id: int):
        user = await self.col.find_one({"id": user_id, "banned": True})
        return bool(user)

    async def ban_user(self, user_id: int):
        await self.col.update_one(
            {"id": user_id},
            {"$set": {"banned": True}},
            upsert=True
        )

    async def unban_user(self, user_id: int):
        await self.col.update_one(
            {"id": user_id},
            {"$set": {"banned": False}},
            upsert=True
        )

    async def total_banned_users_count(self):
        return await self.col.count_documents({"banned": True})

    # ---------------- GROUPS / CHANNELS ---------------- #
    async def total_groups_count(self):
        return await self.col.count_documents({"type": "group"})

    async def total_channels_count(self):
        return await self.col.count_documents({"type": "channel"})

    async def get_all_by_type(self, user_type: str):
        return self.col.find({"type": user_type})

    # ---------------- FILES ---------------- #
    async def add_file(self, file_data: Dict):
        await self.file.insert_one(file_data)

    async def get_file(self, file_id: str):
        return await self.file.find_one({"_id": file_id})

    async def delete_one_file(self, file_id: str):
        await self.file.delete_one({"_id": file_id})

    async def total_files(self):
        return await self.file.count_documents({})

    async def count_links(self, user_id: int, action: str):
        if action == "+":
            await self.col.update_one(
                {"id": user_id},
                {"$inc": {"Links": 1}},
                upsert=True
            )
        elif action == "-":
            await self.col.update_one(
                {"id": user_id},
                {"$inc": {"Links": -1}},
                upsert=True
            )
