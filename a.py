from app import db
from app import Cliente

print([c.name for c in Cliente.__table__.columns])