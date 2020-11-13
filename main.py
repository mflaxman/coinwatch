from io import BytesIO
from os import environ

import asyncio

from buidl.block import Block
from sanic import Sanic
from sanic.response import json

import models
import rpc


PYTHON_HOST = environ.get("PYTHON_HOST", "0.0.0.0")
PYTHON_PORT = int(environ.get("PYTHON_PORT", "8000"))

app = Sanic("Python Bitcoin Core Node Wrapper")


async def do_fetch(db):
    cursor = await db.execute("SELECT height FROM blocks ORDER BY height DESC LIMIT 1")
    row = await cursor.fetchone()
    await cursor.close()  # FIXME: with wrapper
    if row is None:
        db_curr_height = 0
    else:
        db_curr_height = row[0]

    # FIXME: handle orphaned chain!
    core_block_height = await rpc.get_block_count()

    for block_height in range(db_curr_height + 1, core_block_height):
        block_hash = await rpc.get_block_hash(block_height)
        block_hex = await rpc.get_block_hex(block_hash)

        # Attempt to parse the block (TODO: save data)
        block_obj = Block.parse_header(BytesIO(bytes.fromhex(block_hex)))
        assert block_obj.id() == block_hash, "Bad block parse!"
        if block_height % 100 == 0:
            print(f"Parsed {block_height} without error")

        if block_height % 1000 == 0:
            print(f"inserting... {block_height}")
        await models.insert_block(
            db=app.db,
            blockhash_hex=block_obj.id(),
            height=block_height,
            version=block_obj.version,
            prev_hash=block_obj.prev_block,
            merkle_root=block_obj.merkle_root,
            timestamp=block_obj.timestamp,
            bits=block_obj.bits,
            nonce=block_obj.nonce,
        )


async def fetch_block_headers(db):
    while True:
        print("loop")
        await do_fetch(db=db)
        # Wait 60s once up-to-date (TODO: make this even driven)
        await asyncio.sleep(5)


# https://sanic.readthedocs.io/en/0.5.4/sanic/middleware.html#listeners
@app.listener("before_server_start")
async def setup_db(app, loop):
    app.db = await models.db_setup()


# https://github.com/huge-success/sanic/issues/1012#issuecomment-351120972
@app.listener("after_server_start")
async def start_tasks(app, loop):
    app.add_task(fetch_block_headers(db=app.db))


@app.listener("after_server_stop")
async def close_db(app, loop):
    await app.db.close()


@app.get("/core/getblockchaininfo")
async def core_info(request, path=None):

    return json(await rpc.get_blockchain_info())


@app.get("/core/getblockhash/<blockheight:int>")
async def core_blockhash(request, blockheight):

    return json({"block_hash": await rpc.get_block_hash(block_height_int=blockheight)})


@app.get("/core/getblock/<blockhash:string>")
async def core_getblock(request, blockhash):

    return json(
        {
            "block_hex": await rpc.get_block_hex(blockhash),
        }
    )


@app.get("/core/getblockfilter/<blockhash:string>")
async def core_getblockfilter(request, blockhash):

    block_filter = await rpc.get_block_filter(blockhash)
    return json(block_filter)  # TODO: explicitly handle this


@app.get("/status")
async def coinwatcher_status(request):

    return json(
        {
            "sqlite_height": await models.get_latest_blockheight(db=app.db),
            "bitcoin_core": await rpc.get_block_count(),
        }
    )


if __name__ == "__main__":
    print("Running python server on %s:%s" % (PYTHON_HOST, PYTHON_PORT))
    app.run(host=PYTHON_HOST, port=PYTHON_PORT)
