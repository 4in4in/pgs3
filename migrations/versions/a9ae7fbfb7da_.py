"""empty message

Revision ID: a9ae7fbfb7da
Revises: 1031a349622d
Create Date: 2023-07-06 16:21:00.477756

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a9ae7fbfb7da'
down_revision = '1031a349622d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('item', sa.Column('type', sa.String(length=1), nullable=False))
    op.drop_column('item', 'item_type')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('item', sa.Column('item_type', sa.VARCHAR(length=1), autoincrement=False, nullable=False))
    op.drop_column('item', 'type')
    # ### end Alembic commands ###