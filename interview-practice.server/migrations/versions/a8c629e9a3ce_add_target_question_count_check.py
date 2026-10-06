"""add target question count check

Revision ID: a8c629e9a3ce
Revises: ab456f926474
Create Date: 2026-10-06 16:31:55.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'a8c629e9a3ce'
down_revision = 'ab456f926474'
branch_labels = None
depends_on = None


def upgrade():
    # The API already limits the count to 1-30; this makes the table refuse the rest.
    op.create_check_constraint(
        'ck_target_question_count_1_30',
        'interviews',
        'target_question_count BETWEEN 1 AND 30',
    )


def downgrade():
    op.drop_constraint('ck_target_question_count_1_30', 'interviews', type_='check')
