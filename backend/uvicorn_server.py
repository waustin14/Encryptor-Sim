import os
import ssl

import uvicorn


def main() -> None:
    ssl_certfile = os.environ.get("APP_SSL_CERTFILE", "/etc/encryptor-sim/tls/server.crt")
    ssl_keyfile = os.environ.get("APP_SSL_KEYFILE", "/etc/encryptor-sim/tls/server.key")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=443,
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile,
        ssl_version=ssl.PROTOCOL_TLSv1_2,
    )


if __name__ == "__main__":
    main()
