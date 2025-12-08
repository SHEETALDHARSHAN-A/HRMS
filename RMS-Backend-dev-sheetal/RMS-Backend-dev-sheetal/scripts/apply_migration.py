# scripts/apply_migration.py

"""
Apply a SQL migration file using the project's async SQLAlchemy engine.

Usage:
  python -m scripts.apply_migration path/to/migration.sql

This script reads the file, splits statements by ';' and executes them sequentially in a transaction.
It uses the project's `engine` from `app.db.connection_manager` so it reads DB settings from your .env/AppConfig.

Note: For safety, review the SQL file before running in production.
"""

import sys
import asyncio

from sqlalchemy import text
from app.db.connection_manager import engine

async def apply_sql_file(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        sql = f.read()

    def split_statements(sql_text: str) -> list[str]:
        """Split SQL file into statements but respect dollar-quoted blocks ($$...$$ or $tag$...$tag$).

        This is a small parser that avoids splitting inside dollar-quoted function bodies which
        commonly contain semicolons.
        """
        statements = []
        cur = []
        i = 0
        n = len(sql_text)
        in_dollar = False
        dollar_tag = None

        while i < n:
            ch = sql_text[i]
            # detect start of dollar-quote: $tag$
            if not in_dollar and ch == '$':
                # try to read a tag like $tag$
                j = i + 1
                while j < n and (sql_text[j].isalnum() or sql_text[j] == '_'):
                    j += 1
                if j < n and sql_text[j] == '$':
                    # found opening tag
                    dollar_tag = sql_text[i:j+1]
                    in_dollar = True
                    cur.append(dollar_tag)
                    i = j + 1
                    continue

            # detect end of dollar-quote
            if in_dollar and sql_text.startswith(dollar_tag, i):
                cur.append(dollar_tag)
                i += len(dollar_tag)
                in_dollar = False
                dollar_tag = None
                continue

            # when not in dollar-quote, semicolon ends a statement
            if not in_dollar and ch == ';':
                stmt = ''.join(cur).strip()
                if stmt:
                    statements.append(stmt)
                cur = []
                i += 1
                continue

            # otherwise just append the character
            cur.append(ch)
            i += 1

        # append any trailing statement
        trailing = ''.join(cur).strip()
        if trailing:
            statements.append(trailing)

        return statements

    statements = split_statements(sql)

    async with engine.begin() as conn:
        for stmt in statements:
            print(f"Executing statement (truncated): {stmt[:120]}...")
            # Use execute of raw SQL text. Some statements may be DDL or function
            # definitions containing dollar-quoting; SQLAlchemy will pass them through.
            await conn.exec_driver_sql(stmt)
    print("Migration applied successfully.")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.apply_migration path/to/migration.sql")
        sys.exit(1)
    path = sys.argv[1]
    asyncio.run(apply_sql_file(path))
