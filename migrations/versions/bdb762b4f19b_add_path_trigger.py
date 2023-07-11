"""add path trigger

Revision ID: bdb762b4f19b
Revises: d3017aab0d29
Create Date: 2023-07-11 21:05:39.493575

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "bdb762b4f19b"
down_revision = "d3017aab0d29"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE OR REPLACE FUNCTION public._update_item_path()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE pth VARCHAR;
BEGIN
    WITH RECURSIVE items_cte(item_id, name, type, parent_id, path) AS (
        SELECT i.item_id, i."name", i.type, i.parent_id, array[i."name"] AS path
        FROM item i
        WHERE i.parent_id IS NULL
        UNION ALL
        SELECT c.item_id, c."name", c.type, c.parent_id, array_append(p.path, c.name)
        FROM items_cte p
        JOIN item c ON c.parent_id = p.item_id
    )
    SELECT array_to_string(path || array[NEW.name], '/')
    FROM items_cte
    INTO pth
    WHERE items_cte.item_id = NEW.parent_id;
    NEW.path = pth;
    RETURN NEW;
END;
$function$
;"""
    )
    op.execute(
        """CREATE TRIGGER update_item_path BEFORE INSERT OR UPDATE ON item
FOR EACH ROW EXECUTE PROCEDURE _update_item_path();"""
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER update_item_path ON public.item;")
    op.execute("drop function _update_item_path;")
