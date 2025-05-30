import asyncio
from aiosmtpd.controller import Controller
from aiosmtpd.handlers import AsyncMessage
from email.message import Message
from datetime import datetime
import json
import logging
from logger_config import setup_logging
import socket
import threading
import time
from typing import Optional, List, Dict, Any, Tuple
import html2text

# Setup logging
loggers = setup_logging()
logger = loggers["email_server"]


class SimpleEmailHandler(AsyncMessage):
    def __init__(self):
        super().__init__()
        self.messages: List[Dict[str, Any]] = []
        self.connection_count = 0
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = False
        self.html_converter.ignore_emphasis = False
        logger.info("SimpleEmailHandler initialized")

    async def handle_message(self, message: Message) -> None:
        try:
            self.connection_count += 1
            logger.info(f"New email received from {message.get('From', '')}")

            # Get both plain text and HTML content
            plain_text, html_content = self._get_content(message)

            # Convert message to dict format
            msg_dict = {
                "id": id(message),
                "from": message.get("From", ""),
                "to": message.get("To", ""),
                "subject": message.get("Subject", ""),
                "date": message.get("Date", ""),
                "timestamp": datetime.now().isoformat(),
                "body": plain_text,
                "is_html": bool(html_content),
                "html_content": html_content,
                "parsed_html": (
                    self.html_converter.handle(html_content) if html_content else None
                ),
            }

            self.messages.insert(0, msg_dict)  # Add new messages at the beginning
            logger.info(
                f"Email processed successfully. Total messages: {len(self.messages)}"
            )
        except Exception as e:
            logger.error(f"Error processing email: {str(e)}")

    def _get_content(self, message: Message) -> Tuple[str, Optional[str]]:
        """Extract both plain text and HTML content from the message."""
        plain_text = ""
        html_content = None

        try:
            if message.is_multipart():
                # First try to get HTML content
                for part in message.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/html":
                        payload = part.get_payload(decode=True)
                        if isinstance(payload, bytes):
                            html_content = payload.decode()
                        else:
                            html_content = str(payload)
                    elif content_type == "text/plain" and not plain_text:
                        payload = part.get_payload(decode=True)
                        if isinstance(payload, bytes):
                            plain_text = payload.decode()
                        else:
                            plain_text = str(payload)
            else:
                # Single part message
                payload = message.get_payload(decode=True)
                if isinstance(payload, bytes):
                    content = payload.decode()
                else:
                    content = str(payload)

                if message.get_content_type() == "text/html":
                    html_content = content
                else:
                    plain_text = content

            # If we have HTML but no plain text, convert HTML to plain text
            if html_content and not plain_text:
                plain_text = self.html_converter.handle(html_content)
            # If we have no content at all, return error message
            elif not plain_text and not html_content:
                plain_text = "Error reading email body"

            return plain_text, html_content

        except Exception as e:
            logger.error(f"Error getting email content: {str(e)}")
            return "Error reading email body", None

    def get_messages(self) -> List[Dict[str, Any]]:
        return self.messages

    def get_message(self, message_id: int) -> Optional[Dict[str, Any]]:
        for msg in self.messages:
            if msg["id"] == message_id:
                return msg
        return None

    def delete_message(self, message_id: int) -> bool:
        for i, msg in enumerate(self.messages):
            if msg["id"] == message_id:
                self.messages.pop(i)
                logger.info(
                    f"Message {message_id} deleted. Remaining messages: {len(self.messages)}"
                )
                return True
        return False

    def clear_messages(self) -> None:
        self.messages.clear()
        logger.info("All messages cleared")

    def get_connection_count(self) -> int:
        return self.connection_count


class EmailServer:
    def __init__(self, host: str = "localhost", port: int = 1025):
        self.host = host
        self.port = port
        self.handler = SimpleEmailHandler()
        self.controller = None
        self._connection_check_thread = None
        self._stop_connection_check = threading.Event()
        logger.info(f"EmailServer initialized with host={host}, port={port}")

    def _check_connection(self):
        """Periodically check if the server is still responsive"""
        while not self._stop_connection_check.is_set():
            try:
                if self.controller and self.controller.server:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(1)
                        s.connect((self.host, self.port))
                        logger.debug("Connection check successful")
            except Exception as e:
                logger.warning(f"Connection check failed: {str(e)}")
                if self.controller and self.controller.server:
                    try:
                        logger.info("Attempting to restart server...")
                        self.controller.stop()
                        time.sleep(1)
                        self.controller.start()
                        logger.info("Server restarted successfully")
                    except Exception as restart_error:
                        logger.error(f"Failed to restart server: {str(restart_error)}")
            time.sleep(5)

    def _find_available_port(self, start_port: int) -> int:
        """Find an available port starting from start_port."""
        port = start_port
        while port < start_port + 100:  # Try up to 100 ports
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    s.bind((self.host, port))
                    logger.info(f"Found available port: {port}")
                    return port
            except (OSError, socket.timeout) as e:
                logger.warning(f"Port {port} in use or timeout: {str(e)}")
                port += 1
        raise OSError("No available ports found")

    def start(self):
        try:
            self.port = self._find_available_port(self.port)

            self.controller = Controller(
                self.handler,
                hostname=self.host,
                port=self.port,
                auth_required=False,
                server_hostname=self.host,
                timeout=30,
            )

            self.controller.start()
            logger.info(f"Server started on {self.host}:{self.port}")

            # Start connection monitoring
            self._stop_connection_check.clear()
            self._connection_check_thread = threading.Thread(
                target=self._check_connection
            )
            self._connection_check_thread.daemon = True
            self._connection_check_thread.start()

            logger.info(f"Server is listening on {self.host}:{self.port}")

        except OSError as e:
            logger.error(f"Failed to start server: {str(e)}")
            raise OSError(f"Failed to start server: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error starting server: {str(e)}")
            raise

    def stop(self):
        if self.controller:
            try:
                if self._connection_check_thread:
                    self._stop_connection_check.set()
                    self._connection_check_thread.join(timeout=5)

                self.controller.stop()
                self.controller = None
                logger.info("Server stopped gracefully")
            except Exception as e:
                logger.error(f"Error stopping server: {str(e)}")
                raise

    def is_running(self) -> bool:
        return self.controller is not None

    def get_config(self) -> dict:
        return {
            "host": self.host,
            "port": self.port,
            "connection_count": self.handler.get_connection_count(),
        }
