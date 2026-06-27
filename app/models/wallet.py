import mongoengine as db
from datetime import datetime

class Wallet(db.Document):
    meta = {'collection': 'wallets'}
    
    user_id = db.StringField(required=True)
    balance = db.IntField(default=0)
    updated_at = db.DateTimeField(default=datetime.utcnow)

    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return super(Wallet, self).save(*args, **kwargs)

    def __repr__(self):
        return f'<Wallet User:{self.user_id} Balance:{self.balance}>'
