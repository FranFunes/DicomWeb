"""Changed Filter to BasicFilter

Revision ID: 4940a713bd1b
Revises: e60439e1b5ee
Create Date: 2023-08-06 21:48:49.733406

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4940a713bd1b'
down_revision = 'e60439e1b5ee'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('basic_filter',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('field', sa.String(length=64), nullable=True),
    sa.Column('value', sa.String(length=64), nullable=True),
    sa.Column('device_name', sa.String(length=64), nullable=True),
    sa.ForeignKeyConstraint(['device_name'], ['device.name'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('basic_filter', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_basic_filter_field'), ['field'], unique=False)
        batch_op.create_index(batch_op.f('ix_basic_filter_value'), ['value'], unique=False)

    with op.batch_alter_table('filter', schema=None) as batch_op:
        batch_op.drop_index('ix_filter_field')
        batch_op.drop_index('ix_filter_value')

    op.drop_table('filter')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('filter',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('field', sa.VARCHAR(length=64), nullable=True),
    sa.Column('value', sa.VARCHAR(length=64), nullable=True),
    sa.Column('device_name', sa.VARCHAR(length=64), nullable=True),
    sa.ForeignKeyConstraint(['device_name'], ['device.name'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('filter', schema=None) as batch_op:
        batch_op.create_index('ix_filter_value', ['value'], unique=False)
        batch_op.create_index('ix_filter_field', ['field'], unique=False)

    with op.batch_alter_table('basic_filter', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_basic_filter_value'))
        batch_op.drop_index(batch_op.f('ix_basic_filter_field'))

    op.drop_table('basic_filter')
    # ### end Alembic commands ###
