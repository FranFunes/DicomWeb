"""Removed ModalitiesInStudy and added SeriesNumber

Revision ID: 8db23b18e49c
Revises: c71697551827
Create Date: 2023-08-01 10:07:18.252288

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8db23b18e49c'
down_revision = 'c71697551827'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('series', schema=None) as batch_op:
        batch_op.add_column(sa.Column('SeriesNumber', sa.Integer(), nullable=True))

    with op.batch_alter_table('study', schema=None) as batch_op:
        batch_op.drop_index('ix_study_ModalitiesInStudy')
        batch_op.drop_column('ModalitiesInStudy')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('study', schema=None) as batch_op:
        batch_op.add_column(sa.Column('ModalitiesInStudy', sa.VARCHAR(length=64), nullable=True))
        batch_op.create_index('ix_study_ModalitiesInStudy', ['ModalitiesInStudy'], unique=False)

    with op.batch_alter_table('series', schema=None) as batch_op:
        batch_op.drop_column('SeriesNumber')

    # ### end Alembic commands ###