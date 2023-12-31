"""empty message

Revision ID: d3017aab0d29
Revises: a9ae7fbfb7da
Create Date: 2023-07-11 20:37:09.989922

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd3017aab0d29'
down_revision = 'a9ae7fbfb7da'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('item', sa.Column('path', sa.String(), nullable=True))
    op.drop_constraint('item_parent_id_fkey', 'item', type_='foreignkey')
    op.create_foreign_key(None, 'item', 'item', ['parent_id'], ['item_id'], onupdate='CASCADE', ondelete='CASCADE')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'item', type_='foreignkey')
    op.create_foreign_key('item_parent_id_fkey', 'item', 'item', ['parent_id'], ['item_id'], ondelete='CASCADE')
    op.drop_column('item', 'path')
    # ### end Alembic commands ###
