import os
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
from dotenv import load_dotenv


load_dotenv()
PUBLIC_KEY = os.getenv("DISCORD_PUBLIC_KEY")

verify_key = VerifyKey(bytes.fromhex(PUBLIC_KEY))  # type: ignore


def verify_discord_signature(
    signature: str,
    timestamp: str,
    body: bytes,
) -> bool:
    try:
        verify_key.verify(
            timestamp.encode() + body,
            bytes.fromhex(signature)
        )
        return True
    except BadSignatureError:
        return False
