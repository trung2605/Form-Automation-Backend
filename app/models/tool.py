import mongoengine as db
from datetime import datetime

class Tool(db.Document):
    meta = {'collection': 'tools'}
    
    name = db.StringField(required=True)
    description = db.StringField(required=True)
    category = db.StringField(required=True)
    status = db.StringField(default='upcoming') # active, upcoming
    route = db.StringField(default='#')
    icon = db.StringField(required=True)
    created_at = db.DateTimeField(default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'status': self.status,
            'route': self.route,
            'icon': self.icon,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<Tool {self.name}>'
