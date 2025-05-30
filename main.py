import time
import flet as ft
from email_server import EmailServer
import logging
from logger_config import setup_logging
import tempfile
import os
import webbrowser
from pathlib import Path
import html2text
from typing import Optional, List, Dict, Any, Set, Union, cast

# Setup logging
loggers = setup_logging()
logger = loggers["app"]


class EmailTestingApp:
    def __init__(self):
        logger.info("EmailTestingApp initializing...")
        self.email_server: Optional[EmailServer] = None
        self.selected_message: Optional[Dict[str, Any]] = None
        self.read_messages: Set[int] = set()
        self.temp_dir = Path(tempfile.gettempdir()) / "email_testing_server"
        self.temp_dir.mkdir(exist_ok=True)
        self.messages: List[Dict[str, Any]] = []
        self.last_message_count: int = 0
        self.last_read_count: int = 0
        self.total_messages: ft.Text = ft.Text(
            f"Total Messages: {len(self.messages)}",
            color=ft.Colors.WHITE,
        )
        self.message_read_info: ft.Text = ft.Text(
            f"{len(self.read_messages)} / {len(self.messages)}",
            color=ft.Colors.WHITE,
            size=14,
        )
        self._refresh_running: bool = False
        self._last_selected_message: Optional[Dict[str, Any]] = None
        self._initialized: bool = False
        # UI elements
        self.email_list: Optional[ft.Container] = None
        self.start_button: Optional[ft.ElevatedButton] = None
        self.status_text: Optional[ft.Text] = None
        self.config_display: Optional[ft.Container] = None
        self.port_notification: Optional[ft.Text] = None
        logger.info("EmailTestingApp initialized")

    def initialize_server(self) -> None:
        """Initialize the email server if not already initialized."""
        if self.email_server is None:
            logger.info("Initializing email server...")
            self.email_server = EmailServer()
            logger.info("Email server initialized")

    def _create_html_file(self, content: str, message_id: int) -> str:
        """Create a temporary HTML file with the email content."""
        html_file = self.temp_dir / f"email_{message_id}.html"

        # Create a complete HTML document with proper styling that preserves email layout
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    margin: 0;
                    height: 100vh;
                    width: 100vw;
                    display: flex;
                    justify-content: center; /* horizontal center */
                    align-items: center;    /* vertical center */
                    background-color: #f0f0f0;
                    padding: 20px;
                }}
                /* Preserve original email styling */
                * {{
                    max-width: 100%;
                    box-sizing: border-box;
                }}
                img {{
                    max-width: 100%;
                    height: auto;
                    display: inline-block;
                }}
                table {{
                    border-collapse: collapse;
                    margin: 10px 0;
                    width: auto !important;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }}
                th {{
                    background-color: #f5f5f5;
                }}
                pre {{
                    background-color: #f5f5f5;
                    padding: 10px;
                    border-radius: 4px;
                    overflow-x: auto;
                    white-space: pre-wrap;
                }}
                code {{
                    font-family: 'Courier New', Courier, monospace;
                }}
                /* Preserve original colors and styles */
                .email-content {{
                    all: revert;
                    max-width: 800px;
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <div class="email-content">
                {content}
            </div>
        </body>
        </html>
        """

        html_file.write_text(full_html, encoding="utf-8")
        return str(html_file)

    def apply_hover_style(self, button, hover_color, default_color):
        def on_hover(e):
            button.style.bgcolor = hover_color if e.data == "true" else default_color
            button.update()

        return on_hover

    def main(self, page: ft.Page):
        """Main application window."""
        if self._initialized:
            logger.warning("Application already initialized, skipping...")
            return

        logger.info("Starting EmailTestingApp main window")
        self._initialized = True

        # Set up the page
        page.title = "Local Email Testing Server"
        page.theme_mode = ft.ThemeMode.DARK
        page.theme = ft.Theme(font_family="Poppins")
        page.window.maximized = True
        page.window.resizable = True
        page.padding = 20
        page.bgcolor = "#1a1a1a"

        # Initialize server
        self.initialize_server()

        # Server status and controls

        self.status_text = ft.Text(
            "Server Status: Stopped", color="red", size=16, weight=ft.FontWeight.BOLD
        )
        self.start_button = ft.ElevatedButton(
            "Start Server",
            on_click=self.toggle_server,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.GREEN_700,
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
        )
        self.start_button.on_hover = self.apply_hover_style(
            button=self.start_button,
            hover_color=ft.Colors.GREEN_500,
            default_color=ft.Colors.GREEN_700,
        )
        self.clear_button = ft.ElevatedButton(
            "Clear All Emails",
            on_click=self.clear_emails,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.RED_700,
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
        )
        self.clear_button.on_hover = self.apply_hover_style(
            button=self.clear_button,
            hover_color=ft.Colors.RED_500,
            default_color=ft.Colors.RED_700,
        )
        self.refresh_button = ft.ElevatedButton(
            "Refresh",
            on_click=self.refresh_emails,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_700,
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
        )
        self.refresh_button.on_hover = self.apply_hover_style(
            button=self.refresh_button,
            hover_color=ft.Colors.BLUE_500,
            default_color=ft.Colors.BLUE_700,
        )

        # Configuration display
        self.config_text = ft.Text(
            "Server Configuration",
            size=20,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.WHITE,
        )
        self.config_display = ft.Container(
            content=ft.Row([ft.Text("Server not running", color=ft.Colors.GREY_400)]),
            padding=10,
            bgcolor=ft.Colors.BLACK45,
            border_radius=8,
        )
        self.port_notification = ft.Text(
            "", color=ft.Colors.ORANGE, size=14, visible=False
        )

        # Email list
        self.email_list = ft.Container(
            content=ft.ListView(spacing=10, padding=10),
            bgcolor=ft.Colors.BLACK45,
            border_radius=8,
            padding=10,
            width=400,
            height=600,
            expand=True,
        )

        # Email details view
        self.email_details = ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        "Email Details",
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.WHITE,
                    ),
                    ft.Container(
                        content=ft.TextField(
                            label="From",
                            read_only=True,
                            multiline=True,
                            border_color=ft.Colors.BLUE_700,
                            bgcolor=ft.Colors.BLACK45,
                            color=ft.Colors.WHITE,
                        ),
                        padding=5,
                    ),
                    ft.Container(
                        content=ft.TextField(
                            label="To",
                            read_only=True,
                            multiline=True,
                            border_color=ft.Colors.BLUE_700,
                            bgcolor=ft.Colors.BLACK45,
                            color=ft.Colors.WHITE,
                        ),
                        padding=5,
                    ),
                    ft.Container(
                        content=ft.TextField(
                            label="Subject",
                            read_only=True,
                            multiline=True,
                            border_color=ft.Colors.BLUE_700,
                            bgcolor=ft.Colors.BLACK45,
                            color=ft.Colors.WHITE,
                        ),
                        padding=5,
                    ),
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    "Content",
                                    size=16,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.WHITE,
                                ),
                                ft.Tabs(
                                    selected_index=0,
                                    animation_duration=300,
                                    tabs=[
                                        ft.Tab(
                                            text="HTML View",
                                            content=ft.Container(
                                                content=ft.Column(
                                                    [
                                                        ft.Row(
                                                            [
                                                                ft.ElevatedButton(
                                                                    "Open in Browser",
                                                                    icon=ft.Icons.LAUNCH,
                                                                    on_click=lambda e: (
                                                                        self._open_in_browser(
                                                                            e
                                                                        )
                                                                        if self.selected_message
                                                                        else None
                                                                    ),
                                                                    style=ft.ButtonStyle(
                                                                        color=ft.Colors.WHITE,
                                                                        bgcolor=ft.Colors.BLUE_700,
                                                                        shape=ft.RoundedRectangleBorder(
                                                                            radius=8
                                                                        ),
                                                                    ),
                                                                ),
                                                            ],
                                                            alignment=ft.MainAxisAlignment.END,
                                                        ),
                                                        ft.Markdown(
                                                            "",
                                                            selectable=True,
                                                            extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                                                        ),
                                                    ],
                                                    spacing=10,
                                                ),
                                                bgcolor=ft.Colors.BLACK45,
                                                border_radius=8,
                                                padding=10,
                                                expand=True,
                                            ),
                                        ),
                                        ft.Tab(
                                            text="Plain Text",
                                            content=ft.TextField(
                                                read_only=True,
                                                multiline=True,
                                                border_color=ft.Colors.BLUE_700,
                                                bgcolor=ft.Colors.BLACK45,
                                                color=ft.Colors.WHITE,
                                                expand=True,
                                            ),
                                        ),
                                    ],
                                    expand=True,
                                ),
                            ],
                            spacing=10,
                        ),
                        padding=5,
                        expand=True,
                    ),
                    ft.Row(
                        [
                            ft.ElevatedButton(
                                "Delete",
                                on_click=self.delete_selected_email,
                                style=ft.ButtonStyle(
                                    color=ft.Colors.WHITE,
                                    bgcolor=ft.Colors.RED_700,
                                    shape=ft.RoundedRectangleBorder(radius=8),
                                ),
                            ),
                            ft.ElevatedButton(
                                "Close",
                                on_click=self.close_email_details,
                                style=ft.ButtonStyle(
                                    color=ft.Colors.WHITE,
                                    bgcolor=ft.Colors.BLUE_700,
                                    shape=ft.RoundedRectangleBorder(radius=8),
                                ),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
                spacing=10,
            ),
            bgcolor=ft.Colors.BLACK45,
            border_radius=8,
            padding=20,
            expand=True,
            visible=False,
        )

        # Layout
        page.add(
            ft.Container(
                content=ft.Column(
                    [
                        self.config_text,
                        self.config_display,
                        self.port_notification,
                        ft.Row(
                            [
                                self.status_text,
                                self.start_button,
                                self.clear_button,
                                self.refresh_button,
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                    ],
                    spacing=10,
                ),
                padding=10,
                bgcolor=ft.Colors.BLACK45,
                border_radius=8,
            ),
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            ft.Row(
                [
                    ft.Column(
                        [
                            ft.Row(
                                controls=[
                                    ft.Text(
                                        "Email Messages",
                                        size=20,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.WHITE,
                                    ),
                                    self.message_read_info,
                                ],
                                width=400,
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                spacing=10,
                            ),
                            self.email_list,
                        ],
                        spacing=10,
                        width=400,
                    ),
                    ft.VerticalDivider(width=1, color=ft.Colors.GREY_800),
                    self.email_details,
                ],
                expand=True,
                spacing=20,
            ),
        )

        # Start auto-refresh timer
        def auto_refresh():
            if self.email_server.is_running() and not self._refresh_running:
                self.refresh_emails(None)
            page.update()

        while True:
            try:
                auto_refresh()
                time.sleep(5)  # Refresh every 5 seconds
            except Exception as e:
                logger.error(f"Error during auto-refresh: {str(e)}")
                break

    def toggle_server(
        self, e: Optional[Union[ft.ControlEvent, Exception]] = None
    ) -> None:
        """Toggle the email server on/off."""
        if not self.start_button:
            return

        self.start_button.disabled = True
        if not self.email_server:
            self.initialize_server()

        if not self.email_server:  # Double check after initialization
            logger.error("Failed to initialize email server")
            return

        try:
            if self.email_server.is_running():
                logger.info("Stopping email server")
                self.email_server.stop()
                if self.status_text:
                    self.status_text.value = "Server Status: Stopped"
                    self.status_text.color = "red"
                if self.start_button:
                    self.start_button.text = "Start Server"
                    self.start_button.style = ft.ButtonStyle(
                        color=ft.Colors.WHITE,
                        bgcolor=ft.Colors.GREEN_700,
                        shape=ft.RoundedRectangleBorder(radius=8),
                    )
                    self.start_button.on_hover = self.apply_hover_style(
                        button=self.start_button,
                        hover_color=ft.Colors.GREEN_500,
                        default_color=ft.Colors.GREEN_700,
                    )
                if self.config_display:
                    self.config_display.content = ft.Row(
                        [ft.Text("Server not running", color=ft.Colors.GREY_400)]
                    )
                if self.port_notification:
                    self.port_notification.visible = False
            else:
                logger.info("Starting email server")
                self.email_server.start()
                if self.status_text:
                    self.status_text.value = "Server Status: Running"
                    self.status_text.color = "green"
                if self.start_button:
                    self.start_button.text = "Stop Server"
                    self.start_button.style = ft.ButtonStyle(
                        color=ft.Colors.WHITE,
                        bgcolor=ft.Colors.RED_700,
                        shape=ft.RoundedRectangleBorder(radius=8),
                    )
                    self.start_button.on_hover = self.apply_hover_style(
                        button=self.start_button,
                        hover_color=ft.Colors.RED_500,
                        default_color=ft.Colors.RED_700,
                    )
                if self.email_server and self.config_display:
                    config = self.email_server.get_config()
                    # Format configuration display
                    config_text = ft.Row(
                        [
                            ft.Text(f"Host: {config['host']}", color=ft.Colors.WHITE),
                            ft.Text(f"Port: {config['port']}", color=ft.Colors.WHITE),
                            ft.Text(
                                "No Authentication Required",
                                color=ft.Colors.WHITE,
                            ),
                            ft.Text("TLS: Disabled", color=ft.Colors.WHITE),
                            self.total_messages,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    )
                    self.config_display.content = config_text

                    # Show port change notification if port is different from default
                    if self.port_notification:
                        if config["port"] != 1025:
                            self.port_notification.value = f"Note: Using port {config['port']} as port 1025 was in use"
                            self.port_notification.visible = True
                            logger.info(f"Using alternative port: {config['port']}")
                        else:
                            self.port_notification.visible = False
        except Exception as e:
            logger.error(f"Error toggling server: {str(e)}")
            if self.status_text:
                self.status_text.value = f"Server Error: {str(e)}"
                self.status_text.color = "red"
            if self.port_notification:
                self.port_notification.visible = False
        finally:
            # Update all UI elements
            if self.status_text:
                self.status_text.update()
            if self.start_button:
                self.start_button.update()
            if self.config_display:
                self.config_display.update()
            if self.port_notification:
                self.port_notification.update()
            self.refresh_emails(None)
            if self.start_button:
                self.start_button.disabled = False

    def refresh_emails(
        self, e: Optional[Union[ft.ControlEvent, Exception]] = None
    ) -> None:
        """Refresh the email list."""
        if (
            not self.email_server
            or not self.email_server.is_running()
            or self._refresh_running
        ):
            return

        try:
            self._refresh_running = True
            if self.email_server and self.email_server.handler:
                new_messages = self.email_server.handler.get_messages()
                new_read_count = len(self.read_messages)

                # Only update if there are actual changes
                if (
                    len(new_messages) != self.last_message_count
                    or new_read_count != self.last_read_count
                    or any(
                        new_msg["id"] != old_msg["id"]
                        for new_msg, old_msg in zip(new_messages, self.messages)
                    )
                    or (
                        (self.selected_message is None)
                        != (self._last_selected_message is None)
                        or (
                            self.selected_message is not None
                            and self._last_selected_message is not None
                            and self.selected_message["id"]
                            != self._last_selected_message["id"]
                        )
                    )
                ):
                    self.messages = new_messages
                    self.last_message_count = len(new_messages)
                    self.last_read_count = new_read_count
                    self._last_selected_message = self.selected_message

                    # Update message counts
                    self.total_messages.value = f"Total Messages: {len(self.messages)}"
                    self.message_read_info.value = (
                        f"{new_read_count} / {len(self.messages)}"
                    )

                    # Clear and update email list only if needed
                    if self.email_list and hasattr(self.email_list, "content"):
                        content = cast(ft.Container, self.email_list.content)
                        if hasattr(content, "controls"):
                            # Store current scroll position
                            current_scroll = getattr(content, "scroll_offset", 0)

                            # Pre-allocate list for better performance
                            controls = []
                            logger.info(
                                self.selected_message["id"]
                                if self.selected_message
                                else "No selected message"
                            )
                            for msg in self.messages:
                                is_read = msg["id"] in self.read_messages
                                is_selected = (
                                    self.selected_message is not None
                                    and msg["id"] == self.selected_message["id"]
                                )
                                if is_selected:
                                    border_color = ft.Colors.WHITE
                                else:
                                    border_color = ft.Colors.TRANSPARENT
                                if is_read:
                                    bg_color = ft.Colors.BLUE_900
                                else:
                                    bg_color = ft.Colors.BLUE_800
                                controls.append(
                                    ft.Card(
                                        content=ft.Container(
                                            content=ft.Row(
                                                [
                                                    ft.Icon(
                                                        name=(
                                                            ft.Icons.MARK_EMAIL_READ
                                                            if is_read
                                                            else ft.Icons.MARK_EMAIL_UNREAD
                                                        ),
                                                        color=(
                                                            ft.Colors.BLUE_200
                                                            if is_read
                                                            else ft.Colors.WHITE
                                                        ),
                                                        size=20,
                                                    ),
                                                    ft.Column(
                                                        [
                                                            ft.Text(
                                                                f"From: {msg['from']}",
                                                                weight=ft.FontWeight.BOLD,
                                                                color=(
                                                                    ft.Colors.BLUE_200
                                                                    if is_read
                                                                    else ft.Colors.WHITE
                                                                ),
                                                                max_lines=1,
                                                                overflow=ft.TextOverflow.ELLIPSIS,
                                                                expand=1,
                                                            ),
                                                            ft.Text(
                                                                f"Subject: {msg['subject']}",
                                                                color=(
                                                                    ft.Colors.BLUE_200
                                                                    if is_read
                                                                    else ft.Colors.WHITE
                                                                ),
                                                                max_lines=1,
                                                                overflow=ft.TextOverflow.ELLIPSIS,
                                                                expand=1,
                                                            ),
                                                            ft.Text(
                                                                f"Date: {msg['date']}",
                                                                color=ft.Colors.GREY_400,
                                                                size=12,
                                                                max_lines=1,
                                                                overflow=ft.TextOverflow.ELLIPSIS,
                                                                expand=1,
                                                            ),
                                                        ],
                                                        spacing=5,
                                                        expand=True,
                                                    ),
                                                ],
                                                spacing=10,
                                                tight=True,
                                            ),
                                            width=380,
                                            padding=10,
                                            bgcolor=bg_color,
                                            border=ft.border.all(
                                                width=2,
                                                color=border_color,
                                            ),
                                            border_radius=8,
                                            on_click=lambda e, m=msg: self.show_email_details(
                                                m
                                            ),
                                        ),
                                        elevation=3 if is_selected else 1,
                                    )
                                )

                            # Batch update controls
                            content.controls.clear()
                            content.controls.extend(controls)

                            # Restore scroll position if possible
                            try:
                                content.scroll_offset = current_scroll
                            except:
                                pass

                            # Batch update UI
                            self.email_list.update()
                            self.total_messages.update()
                            self.message_read_info.update()

        except Exception as e:
            logger.error(f"Error refreshing emails: {str(e)}")
        finally:
            self._refresh_running = False

    def _open_in_browser(self, e):
        """Open the HTML content in the default web browser."""
        if self.selected_message and self.selected_message.get("html_content"):
            try:
                html_file = self._create_html_file(
                    self.selected_message["html_content"], self.selected_message["id"]
                )
                webbrowser.open(f"file://{html_file}")
                logger.info(
                    f"Opened HTML content in browser for email {self.selected_message['id']}"
                )
            except Exception as e:
                logger.error(f"Error opening HTML content in browser: {str(e)}")

    def show_email_details(self, message):
        try:
            self.selected_message = message
            self.read_messages.add(message["id"])  # Mark as read when opened

            # Update header fields
            self.email_details.content.controls[1].content.value = message["from"]
            self.email_details.content.controls[2].content.value = message["to"]
            self.email_details.content.controls[3].content.value = message["subject"]

            # Get the content tabs container
            content_tabs = self.email_details.content.controls[4].content.controls[1]

            # Update HTML view
            if message.get("is_html") and message.get("html_content"):
                # Create a temporary HTML file for the email content
                html_file = self._create_html_file(
                    message["html_content"], message["id"]
                )
                # Convert HTML to Markdown for display
                h = html2text.HTML2Text()
                h.ignore_links = False
                h.ignore_images = False
                h.ignore_emphasis = False
                markdown_content = h.handle(message["html_content"])
                content_tabs.tabs[0].content.content.controls[
                    1
                ].value = markdown_content
                # Update the container to use a fixed width and center the content
                content_tabs.tabs[0].content.content.controls[1].width = 800
                content_tabs.tabs[0].content.content.controls[
                    1
                ].alignment = ft.MainAxisAlignment.CENTER
            else:
                content_tabs.tabs[0].content.content.controls[1].value = message["body"]

            # Update plain text view
            content_tabs.tabs[1].content.value = message["body"]

            # Reset to first tab
            content_tabs.selected_index = 0

            self.email_details.visible = True
            self.email_details.update()
            self.refresh_emails(None)  # Refresh to update read status
            logger.info(f"Showing details for email from {message['from']}")
        except Exception as e:
            logger.error(f"Error showing email details: {str(e)}")

    def close_email_details(self, e):
        self.email_details.visible = False
        self.email_details.update()
        logger.info("Email details view closed")

    def delete_selected_email(self, e):
        if self.selected_message:
            try:
                # Store message info before deletion
                message_id = self.selected_message["id"]
                message_from = self.selected_message["from"]

                # Delete from server first
                if self.email_server.handler.delete_message(message_id):
                    # Remove from read messages set
                    self.read_messages.discard(message_id)
                    # Clear the selected message
                    self.selected_message = None
                    # Close the details view
                    self.close_email_details(e)
                    # Refresh the email list immediately
                    self.refresh_emails(e)
                    logger.info(f"Deleted email from {message_from}")
                else:
                    logger.error("Failed to delete email from server")
            except Exception as e:
                logger.error(f"Error deleting email: {str(e)}")

    def clear_emails(self, e):
        try:
            self.email_server.handler.clear_messages()
            self.read_messages.clear()  # Clear read status
            if hasattr(self.email_list.content, "controls"):
                self.email_list.content.controls.clear()
            self.email_list.update()
            self.close_email_details(e)
            logger.info("All emails cleared")
        except Exception as e:
            logger.error(f"Error clearing emails: {str(e)}")

    def __del__(self):
        """Clean up temporary files when the app is closed."""
        try:
            self._refresh_running = True  # Stop any ongoing refresh
            for file in self.temp_dir.glob("email_*.html"):
                try:
                    file.unlink()
                except Exception as e:
                    logger.error(f"Error deleting file {file}: {str(e)}")
            try:
                self.temp_dir.rmdir()
            except Exception as e:
                logger.error(f"Error removing temp directory: {str(e)}")
        except Exception as e:
            logger.error(f"Error cleaning up temporary files: {str(e)}")


def main():
    """Main entry point for the application."""
    try:
        logger.info("Starting Email Testing Server application")
        app = EmailTestingApp()
        ft.app(target=app.main)
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        raise


if __name__ == "__main__":
    main()
