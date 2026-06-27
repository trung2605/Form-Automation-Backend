import mongoengine as db
from datetime import datetime

class Transaction(db.Document):
    meta = {'collection': 'transactions'}
    
    user_id = db.StringField(required=True)
    amount = db.IntField(required=True)
    transaction_type = db.StringField(required=True, max_length=50)
    status = db.StringField(default='completed', max_length=20)
    description = db.StringField(max_length=255)
    created_at = db.DateTimeField(default=datetime.utcnow)

    def __repr__(self):
        return f'<Transaction {self.id} User:{self.user_id} Amount:{self.amount}>'
