from typing import Dict

from database.database import get_db


class ReceiptService:
    def __init__(self) -> None:
        self.db = get_db()

    def save_receipt(self, order_id: str, file_path: str) -> Dict[str, str]:
        document = {"order_id": order_id, "file_path": file_path}
        result = self.db.receipts.insert_one(document)
        document["_id"] = str(result.inserted_id)
        return document
