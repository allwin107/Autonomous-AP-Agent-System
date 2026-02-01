from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

class Database:
    client: AsyncIOMotorClient = None
    
    def connect(self):
        self.client = AsyncIOMotorClient(settings.MONGODB_URL)
        
    def close(self):
        if self.client:
            self.client.close()
            
    def get_db(self):
        return self.client[settings.DB_NAME]

db = Database()

def get_database():
    return db.get_db()
