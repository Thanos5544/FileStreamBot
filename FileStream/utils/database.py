import motor.motor_asyncio


class Database:
    def __init__(self, uri, db_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[db_name]
        self.col = self.db["users"]
        self.file = self.db["files"]

    async def add_user(self, user_id: int, u_type="user"):
        await self.col.update_one(
            {"id": user_id},
            {"$set": {"id": user_id, "type": u_type}},
            upsert=True
        )

    async def get_user(self, user_id: int):
        return await self.col.find_one({"id": user_id})

    async def get_all_users(self):
        return self.col.find({})

    async def total_users_count(self):
        return await self.col.count_documents({"type": "user"})

    async def total_groups_count(self):
        return await self.col.count_documents({"type": "group"})

    async def total_channels_count(self):
        return await self.col.count_documents({"type": "channel"})

    async def get_all_by_type(self, t):
        return self.col.find({"type": t})

    async def is_user_banned(self, user_id: int):
        u = await self.col.find_one({"id": user_id, "banned": True})
        return bool(u)

    async def ban_user(self, user_id: int):
        await self.col.update_one({"id": user_id}, {"$set": {"banned": True}}, upsert=True)

    async def unban_user(self, user_id: int):
        await self.col.update_one({"id": user_id}, {"$set": {"banned": False}}, upsert=True)

    async def total_banned_users_count(self):
        return await self.col.count_documents({"banned": True})

    async def delete_user(self, user_id: int):
        await self.col.delete_one({"id": user_id})

    async def add_file(self, data):
        await self.file.insert_one(data)

    async def get_file(self, fid):
        return await self.file.find_one({"_id": fid})

    async def delete_one_file(self, fid):
        await self.file.delete_one({"_id": fid})

    async def total_files(self):
        return await self.file.count_documents({})

    async def count_links(self, uid, action):
        if action == "+":
            await self.col.update_one({"id": uid}, {"$inc": {"Links": 1}}, upsert=True)
        else:
            await self.col.update_one({"id": uid}, {"$inc": {"Links": -1}}, upsert=True)
