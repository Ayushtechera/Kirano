"""empty migration to maintain revision history"""

from typing import Sequence, Union

from alembic import op

revision: str = 'f52624e15bc7'
down_revision: Union[str, Sequence[str], None] = 'a0a398013998'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass