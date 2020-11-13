from io import BytesIO
from os import environ

import aiosqlite
import asyncio

from bitcoinrpc import BitcoinRPC
from bitcoinrpc.bitcoin_rpc import RPCError
from buidl.block import Block
from sanic import Sanic
from sanic.response import json


CORE_HOST = environ.get("CORE_HOST", "localhost")
CORE_PORT = int(environ.get("CORE_PORT", "18332"))  # default to testnet
CORE_USER = environ.get("CORE_USER")
if not CORE_USER:
    raise Exception("Must supply CORE_USER")
CORE_PASSWORD = environ.get("CORE_PASSWORD")
if not CORE_PASSWORD:
    raise Exception("Must supply CORE_PASSWORD")


PYTHON_HOST = environ.get("PYTHON_HOST", "0.0.0.0")
PYTHON_PORT = int(environ.get("PYTHON_PORT", "8000"))

print(
    "Remote Bitcoin Core RPC Server: %s@%s:%s:%s"
    % (CORE_USER, CORE_PASSWORD, CORE_HOST, CORE_PORT)
)

rpc = BitcoinRPC(CORE_HOST, CORE_PORT, CORE_USER, CORE_PASSWORD)

app = Sanic("Python Bitcoin Core Node Wrapper")

DB_STRING = "/Users/mflaxman/coinwatch.sqlite"
# DB_STRING = ":memory:"
CREATE_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS blocks (height integer primary key asc, hash string)""",
    """CREATE UNIQUE INDEX IF NOT EXISTS idx_block_hash ON blocks (hash);""",
]


async def do_fetch(db):
    cursor = await db.execute("SELECT height FROM blocks ORDER BY height DESC LIMIT 1")
    row = await cursor.fetchone()
    await cursor.close()  # FIXME: with wrapper
    if row is None:
        db_curr_height = 0
    else:
        db_curr_height = row[0]

    # FIXME: handle orphaned chain!
    core_res = await make_bitcoin_core_request(
        method="getblockcount",
    )

    if core_res["error"]:
        print("ERROR!", core_res)
        return

    for block_height in range(db_curr_height + 1, core_res["result"]):
        core_res = await make_bitcoin_core_request(
            method="getblockhash",
            params=[block_height],
        )
        if core_res["error"]:
            print("subfetch error", core_res)
            return

        blockhash = core_res["result"]
        core_res = await make_bitcoin_core_request(
            method="getblock",
            params=[blockhash, 0],  # 0 verbosity for hex
        )
        if core_res["error"]:
            print("subsubfetch error", core_res)
            return

        # Attempt to parse the block (TODO: save data)
        block_obj = Block.parse_header(BytesIO(bytes.fromhex(core_res["result"])))
        assert block_obj.id() == blockhash, "Bad block parse!"
        if block_height % 10 == 0:
            print("Parsed without error")

        if block_height % 1000 == 0:
            print(f"inserting... {block_height}")
        await app.db.execute(
            "INSERT INTO blocks(height, hash) values (?, ?)",
            [block_height, core_res["result"]],
        )  # FIXME: named args
        await app.db.commit()


async def fetch_block_headers(db):
    while True:
        print("loop")
        await do_fetch(db=db)
        # Wait 60s once up-to-date (TODO: make this even driven)
        await asyncio.sleep(5)


async def db_setup():
    print("Connecting to sqlite3 DB {DB_STRING}...")
    db = await aiosqlite.connect(DB_STRING)
    for create_statement in CREATE_STATEMENTS:
        await db.execute(create_statement)
    return db


# https://sanic.readthedocs.io/en/0.5.4/sanic/middleware.html#listeners
@app.listener("before_server_start")
async def setup_db(app, loop):
    app.db = await db_setup()


# https://github.com/huge-success/sanic/issues/1012#issuecomment-351120972
@app.listener("after_server_start")
async def start_tasks(app, loop):
    app.add_task(fetch_block_headers(db=app.db))


@app.listener("after_server_stop")
async def close_db(app, loop):
    await app.db.close()


async def make_bitcoin_core_request(method, params=[]):
    print(f"Querying bitcoin core with {method}: {params}")
    try:
        res = await rpc.acall(method, params)
        print("SUCCESS", res)
        return {
            "result": res,
            "error": None,
        }
    except RPCError as e:
        print("ERROR", e.code, e.message)
        return {
            "error": {
                "message": e.message,
                "code": e.code,
            },
            "result": None,
        }


@app.get("/core/getblockchaininfo")
async def wrapper(request, path=None):

    to_return = await make_bitcoin_core_request(
        method="getblockchaininfo",
    )
    return json(to_return)


@app.get("/core/getblockhash/<blockheight:int>")
async def wrapper(request, blockheight):

    cursor = await app.db.execute("SELECT hash FROM blocks")
    row = await cursor.fetchone()
    await cursor.close()  # FIXME: with wrapper
    print("ROW", row)

    if row:
        print("Found in sqlite")
        return json({"result": row[0], "error": None})

    to_return = await make_bitcoin_core_request(
        method="getblockhash",
        params=[blockheight],
    )
    # FIXME: error handling
    print("inserting...")
    await app.db.execute(
        "INSERT INTO blocks(height, hash) values (?, ?)",
        [blockheight, to_return["result"]],
    )  # FIXME: named args
    await app.db.commit()

    return json(to_return)


@app.get("/core/getblock/<blockhash:string>")
async def wrapper(request, blockhash):

    to_return = await make_bitcoin_core_request(
        method="getblock",
        params=[blockhash, 0],  # 0 verbosity for hex
    )
    return json(to_return)


@app.get("/core/getblockfilter/<blockhash:string>")
async def wrapper(request, blockhash):

    to_return = await make_bitcoin_core_request(
        method="getblockfilter",
        params=[blockhash],  # 0 verbosity for hex
    )
    return json(to_return)


@app.get("/status")
async def wrapper(request):

    cursor = await app.db.execute(
        "SELECT height FROM blocks ORDER BY height DESC LIMIT 1"
    )
    row = await cursor.fetchone()
    await cursor.close()  # FIXME: with wrapper
    print("ROW", row)

    to_return = await make_bitcoin_core_request(
        method="getblockcount",
    )
    assert to_return["error"] is None
    return json({"sqlite_height": row[0], "bitcoin_core": to_return["result"]})


if __name__ == "__main__":
    print("Running python server on %s:%s" % (PYTHON_HOST, PYTHON_PORT))
    app.run(host=PYTHON_HOST, port=PYTHON_PORT)
