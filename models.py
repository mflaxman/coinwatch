import aiosqlite

from os import environ

DB_PATH = environ.get("DB_PATH", "/Users/mflaxman/coinwatch.sqlite")
# DB_PATH = ":memory:"


CREATE_STATEMENTS = (
    "CREATE TABLE IF NOT EXISTS blocks ("
    "hash STRING PRIMARY KEY NOT NULL,"
    "height INT,"
    "version INT NOT NULL,"
    "prev_hash STRING NOT NULL,"
    "merkle_root STRING NOT NULL,"
    "timestamp STRING NOT NULL,"
    "bits INT NOT NULL,"
    "nonce INT NOT NULL"
    ");",
    "CREATE INDEX IF NOT EXISTS blocks_height ON blocks(height);",
    "CREATE INDEX IF NOT EXISTS blocks_prevhash ON blocks(prev_hash);",
)

# SQL CLEANUPS TODO:
# named args
# use with wrapper instead of cursor.close()


async def db_setup():
    print("Connecting to sqlite3 DB {DB_PATH}...")
    db = await aiosqlite.connect(DB_PATH)
    for create_statement in CREATE_STATEMENTS:
        print(f"Executing... {create_statement}")
        await db.execute(create_statement)
    return db


async def get_block(db, blockhash_hex):
    cursor = await db.execute(
        "SELECT height, hash FROM blocks WHERE hash = (?)", [blockhash_hex]
    )
    row = await cursor.fetchone()
    await cursor.close()
    if not row:
        return {}
    return {
        "hash": blockhash_hex,
        "height": row["height"],
    }


async def insert_block(
    db, blockhash_hex, height, version, prev_hash, merkle_root, timestamp, bits, nonce
):
    await db.execute(
        "INSERT INTO blocks(hash, height, version, prev_hash, merkle_root, timestamp, bits, nonce) values (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            blockhash_hex,
            height,
            version,
            prev_hash,
            merkle_root,
            timestamp,
            bits,
            nonce,
        ],
    )
    await db.commit()
    # TODO: return insterted row?


async def get_latest_blockheight(db):
    cursor = await db.execute("SELECT height FROM blocks ORDER BY height DESC LIMIT 1")
    row = await cursor.fetchone()
    await cursor.close()
    return row[0]
    print("ROW", row)
