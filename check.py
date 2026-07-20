# check.py
from app.config import settings
from app.database import Base
import app.models

print('All models loaded:')
for t in Base.metadata.tables:
    print(' -', t)