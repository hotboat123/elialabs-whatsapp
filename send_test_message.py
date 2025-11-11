"""
Utility script to send a WhatsApp test message using the configured API client.

Usage:
    python send_test_message.py --to 56912345678 --message "Hola 👋"

Environment:
    Requires the same environment variables defined in `.env` (see `env.example`).
"""

import argparse
import asyncio
import logging
from typing import Final

from app.utils.phone import normalize_phone_number
from app.whatsapp.client import WhatsAppClient


DEFAULT_MESSAGE: Final[str] = "Hola, este es un mensaje de prueba enviado desde la integración de EliaLabs."


async def send_message(to: str, message: str) -> None:
    """Send a text message using the WhatsApp client."""

    client = WhatsAppClient()
    response = await client.send_text_message(to=to, message=message)
    logging.info("WhatsApp API response: %s", response)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Send a WhatsApp test message using the configured Business API credentials.",
    )
    parser.add_argument(
        "--to",
        required=True,
        help="Número de destino con código de país (se aceptan '+', espacios o guiones).",
    )
    parser.add_argument(
        "--message",
        default=DEFAULT_MESSAGE,
        help="Mensaje de texto a enviar. Si no se especifica, se usa uno de prueba.",
    )

    args = parser.parse_args()

    normalized_number = normalize_phone_number(args.to)

    if not normalized_number:
        raise ValueError("El número de destino quedó vacío después de normalizarlo. Verifica el formato.")

    if not normalized_number.isdigit():
        raise ValueError("El número de destino debe contener solo dígitos después de normalizarlo.")

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logging.info("Enviando mensaje de prueba a %s", normalized_number)

    asyncio.run(send_message(normalized_number, args.message))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logging.error("Error al enviar el mensaje: %s", exc)
        raise


