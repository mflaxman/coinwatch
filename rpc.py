from bitcoinrpc import BitcoinRPC
from bitcoinrpc.bitcoin_rpc import RPCError

from os import environ


CORE_HOST = environ.get("CORE_HOST", "localhost")
CORE_PORT = int(environ.get("CORE_PORT", "18332"))  # default to testnet
CORE_USER = environ.get("CORE_USER")
if not CORE_USER:
    raise Exception("Must supply CORE_USER")
CORE_PASSWORD = environ.get("CORE_PASSWORD")
if not CORE_PASSWORD:
    raise Exception("Must supply CORE_PASSWORD")


print(
    "Remote Bitcoin Core RPC Server: %s@%s:%s:%s"
    % (CORE_USER, CORE_PASSWORD, CORE_HOST, CORE_PORT)
)
rpc = BitcoinRPC(
    CORE_HOST, CORE_PORT, CORE_USER, CORE_PASSWORD
)  # TODO: test this at boot?


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


async def get_block_count():
    return await rpc.acall(method="getblockcount", params=[])


async def get_block_hash(block_height_int):
    return await rpc.acall(method="getblockhash", params=[block_height_int])


async def get_block_hex(blockhash_hex):
    # 0 verbosity for hex
    return await rpc.acall(method="getblock", params=[blockhash_hex, 0])


async def get_block_filter(blockhash_hex):
    # 0 verbosity for hex
    return await rpc.acall(
        method="getblockfilter",
        params=[blockhash_hex],  # 0 verbosity for hex
    )


async def get_blockchain_info():
    # 0 verbosity for hex
    return await rpc.acall(
        method="getblockchaininfo",
        params=[],
    )
