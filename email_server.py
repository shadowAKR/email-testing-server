import asyncio
from aiosmtpd.controller import Controller
from email import message_from_bytes
from datetime import datetime
import json
import os
from typing import List, Dict, Optional, Tuple, Any
import socket
import logging
import html2text
import emoji
import ssl
from logger_config import setup_logging
import threading
import time

# Setup logging
loggers = setup_logging()
logger = loggers["email_server"]
smtp_logger = loggers["smtp"]


class EmailMessage:
    def __init__(self, data: bytes):
        self.message = message_from_bytes(data)
        self.timestamp = datetime.now()
        self.id = id(self)
        logger.info(
            f"New email received - From: {self.message.get('from', '')}, Subject: {self.message.get('subject', '')}"
        )

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "from": self.message.get("from", ""),
            "to": self.message.get("to", ""),
            "subject": self.message.get("subject", ""),
            "date": self.message.get("date", ""),
            "timestamp": self.timestamp.isoformat(),
            "body": self._get_body(),
            "is_html": self._is_html(),
            "html_content": self._get_html_content() if self._is_html() else None,
        }

    def _is_html(self) -> bool:
        if self.message.is_multipart():
            for part in self.message.walk():
                if part.get_content_type() == "text/html":
                    return True
        return False

    def _get_html_content(self) -> Optional[str]:
        if self.message.is_multipart():
            for part in self.message.walk():
                if part.get_content_type() == "text/html":
                    return part.get_payload(decode=True).decode()
        return None

    def _get_body(self) -> str:
        try:
            if self.message.is_multipart():
                # First try to get HTML content
                html_content = self._get_html_content()
                if html_content:
                    # Convert HTML to readable text while preserving emojis
                    h = html2text.HTML2Text()
                    h.ignore_links = False
                    h.ignore_images = False
                    h.ignore_emphasis = False
                    return h.handle(html_content)

                # If no HTML, try to get plain text
                for part in self.message.walk():
                    if part.get_content_type() == "text/plain":
                        return part.get_payload(decode=True).decode()
            return self.message.get_payload(decode=True).decode()
        except Exception as e:
            logger.error(f"Error getting email body: {str(e)}")
            return "Error reading email body"


class EmailHandler:
    def __init__(self, username: str = "", password: str = ""):
        self.messages: List[EmailMessage] = []
        self.max_messages = 50
        self.connection_count = 0
        self.username = username
        self.password = password
        logger.info("EmailHandler initialized")

    async def handle_AUTH(
        self, server, session, envelope, mechanism: str, auth_data: bytes
    ) -> Tuple[bool, bool]:
        """
        Handle SMTP authentication.
        Returns a tuple of (success, handled)
        """
        if not self.username or not self.password:
            logger.info("Authentication attempted but not configured")
            return False, True

        try:
            if mechanism.upper() == "PLAIN":
                auth_string = auth_data.decode()
                parts = auth_string.split("\0")
                if len(parts) == 3:
                    auth_username = parts[1]
                    auth_password = parts[2]
                    if (
                        auth_username == self.username
                        and auth_password == self.password
                    ):
                        logger.info(
                            f"Successful authentication for user: {auth_username}"
                        )
                        return True, True
            logger.warning(f"Authentication failed for mechanism: {mechanism}")
            return False, True
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False, True

    async def handle_DATA(self, server, session, envelope):
        try:
            self.connection_count += 1
            logger.info(f"New connection from {session.peer}")
            message = EmailMessage(envelope.content)
            self.messages.insert(0, message)  # Add new messages at the beginning
            if len(self.messages) > self.max_messages:
                self.messages.pop()  # Remove oldest message
            logger.info(
                f"Email processed successfully. Total messages: {len(self.messages)}"
            )
            return "250 Message accepted for delivery"
        except Exception as e:
            logger.error(f"Error processing email: {str(e)}")
            return "550 Error processing message"

    def get_messages(self) -> List[Dict]:
        return [msg.to_dict() for msg in self.messages]

    def get_message(self, message_id: int) -> Optional[Dict]:
        for msg in self.messages:
            if msg.id == message_id:
                return msg.to_dict()
        return None

    def delete_message(self, message_id: int) -> bool:
        for i, msg in enumerate(self.messages):
            if msg.id == message_id:
                self.messages.pop(i)
                logger.info(
                    f"Message {message_id} deleted. Remaining messages: {len(self.messages)}"
                )
                return True
        return False

    def clear_messages(self):
        self.messages.clear()
        logger.info("All messages cleared")

    def get_connection_count(self) -> int:
        return self.connection_count


class EmailServer:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 1025,
        username: str = "",
        password: str = "",
        use_tls: bool = False,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.handler = EmailHandler(username=username, password=password)
        self.controller: Optional[Controller] = None
        self._connection_check_thread = None
        self._stop_connection_check = threading.Event()
        logger.info(
            f"EmailServer initialized with host={host}, port={port}, TLS={use_tls}, Auth={'Enabled' if username and password else 'Disabled'}"
        )

    def _check_connection(self):
        """Periodically check if the server is still responsive"""
        while not self._stop_connection_check.is_set():
            try:
                if self.controller and self.controller.server:
                    # Try to connect to the server
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
            time.sleep(5)  # Check every 5 seconds

    def _find_available_port(self, start_port: int) -> int:
        """Find an available port starting from start_port."""
        port = start_port
        while port < start_port + 100:  # Try up to 100 ports
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)  # Set timeout for socket operations
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

            # Configure SSL context if TLS is enabled
            ssl_context = None
            if self.use_tls:
                ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                # Generate self-signed certificate if it doesn't exist
                cert_path = os.path.join(os.path.dirname(__file__), "server.crt")
                key_path = os.path.join(os.path.dirname(__file__), "server.key")

                if not (os.path.exists(cert_path) and os.path.exists(key_path)):
                    logger.info("Generating self-signed certificate for TLS")
                    os.system(
                        f"openssl req -x509 -newkey rsa:4096 -keyout {key_path} -out {cert_path} -days 365 -nodes -subj '/CN=localhost'"
                    )

                ssl_context.load_cert_chain(cert_path, key_path)
                logger.info("TLS certificate loaded successfully")

            # Configure server with timeout settings
            self.controller = Controller(
                self.handler,
                hostname=self.host,
                port=self.port,
                auth_required=bool(self.username and self.password),
                auth_require_tls=self.use_tls,
                server_hostname=self.host,
                ssl_context=ssl_context,
                timeout=30,  # Set timeout to 30 seconds
            )

            # Start the server
            self.controller.start()
            logger.info(
                f"Server started on {self.host}:{self.port} with TLS={self.use_tls}"
            )

            # Start connection monitoring
            self._stop_connection_check.clear()
            self._connection_check_thread = threading.Thread(
                target=self._check_connection
            )
            self._connection_check_thread.daemon = True
            self._connection_check_thread.start()

            # Log connection information
            logger.info(f"Server is listening on {self.host}:{self.port}")
            if self.username and self.password:
                logger.info("Authentication is enabled")
            if self.use_tls:
                logger.info("TLS is enabled")

        except OSError as e:
            logger.error(f"Failed to start server: {str(e)}")
            raise OSError(f"Failed to start server: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error starting server: {str(e)}")
            raise

    def stop(self):
        if self.controller:
            try:
                # Stop connection monitoring
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

    def get_config(self) -> Dict:
        return {
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "tls": self.use_tls,
            "connection_count": self.handler.get_connection_count(),
        }
