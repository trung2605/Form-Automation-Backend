import mongoengine as db
from datetime import datetime

class User(db.Document):
    meta = {'collection': 'users'}
    
    email = db.StringField(required=True, unique=True, max_length=120)
    password_hash = db.StringField(required=True)
    role = db.StringField(default='user', max_length=20)
    is_banned = db.BooleanField(default=False)
    created_at = db.DateTimeField(default=datetime.utcnow)
    
    @property
    def wallet(self):
        from app.models.wallet import Wallet
        return Wallet.objects(user_id=str(self.id)).first()

    def __repr__(self):
        return f'<User {self.email}>'
