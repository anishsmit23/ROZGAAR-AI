"""Database model package.

Import model modules here so that `Base.metadata` is populated on application import
and tools like Alembic and `Base.metadata.create_all()` see all mapped tables.
"""

# Import individual model modules to register them with SQLAlchemy's metadata
from . import agent_event  # noqa: F401
from . import agent_run  # noqa: F401
from . import application  # noqa: F401
from . import job_posting  # noqa: F401
from . import user  # noqa: F401
