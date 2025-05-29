import flet as ft
from email_server import EmailServer
import json
import logging
import time
import html
from logger_config import setup_logging

# Setup logging
loggers = setup_logging()
logger = loggers["app"]


class EmailTestingApp:
    def __init__(self):
        self.email_server = EmailServer()
        self.selected_message = None
        self.read_messages = set()  # Track read message IDs
        self.last_refresh_time = 0
        self.refresh_interval = 5  # seconds
        logger.info("EmailTestingApp initialized")

    def main(self, page: ft.Page):
        logger.info("Starting EmailTestingApp main window")
        page.title = "Local Email Testing Server"
        page.theme_mode = ft.ThemeMode.DARK
        page.window_width = 1200
        page.window_height = 800
        page.padding = 20
        page.bgcolor = "#1a1a1a"

        # Server settings
        self.username_field = ft.TextField(
            label="Username",
            hint_text="Leave empty for no authentication",
            border_color=ft.Colors.BLUE_700,
            bgcolor=ft.Colors.BLACK45,
            color=ft.Colors.WHITE,
            visible=True,  # Initially visible since server starts stopped
        )
        self.password_field = ft.TextField(
            label="Password",
            hint_text="Leave empty for no authentication",
            password=True,
            can_reveal_password=True,
            border_color=ft.Colors.BLUE_700,
            bgcolor=ft.Colors.BLACK45,
            color=ft.Colors.WHITE,
            visible=True,  # Initially visible since server starts stopped
        )
        self.tls_switch = ft.Switch(
            label="Enable TLS",
            value=False,
            label_style=ft.TextStyle(color=ft.Colors.WHITE),
            visible=True,  # Initially visible since server starts stopped
        )

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
        self.clear_button = ft.ElevatedButton(
            "Clear All Emails",
            on_click=self.clear_emails,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.RED_700,
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
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

        # Configuration display
        self.config_text = ft.Text(
            "Server Configuration",
            size=20,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.WHITE,
        )
        self.config_display = ft.Container(
            content=ft.Column(
                [ft.Text("Server not running", color=ft.Colors.GREY_400)]
            ),
            padding=10,
            bgcolor=ft.Colors.BLACK45,
            border_radius=8,
            width=300,
        )
        self.port_notification = ft.Text(
            "", color=ft.Colors.ORANGE, size=14, visible=False
        )

        # Email list
        self.email_list = ft.Container(
            content=ft.ListView(spacing=10, padding=10, auto_scroll=True, height=400),
            bgcolor=ft.Colors.BLACK45,
            border_radius=8,
            padding=10,
            width=300,
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
                        content=ft.Markdown(
                            "",
                            selectable=True,
                            extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                            code_theme="atom-one-dark",
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
                        ft.Text(
                            "Server Settings",
                            size=20,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.WHITE,
                        ),
                        self.username_field,
                        self.password_field,
                        self.tls_switch,
                        ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
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
                            self.config_text,
                            self.config_display,
                            self.port_notification,
                            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                            ft.Text(
                                "Email Messages",
                                size=20,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.WHITE,
                            ),
                            self.email_list,
                        ],
                        spacing=10,
                    ),
                    ft.VerticalDivider(width=1, color=ft.Colors.GREY_800),
                    self.email_details,
                ],
                expand=True,
                spacing=20,
            ),
        )

        # Start auto-refresh timer
        def auto_refresh(e):
            if self.email_server.is_running():
                self.refresh_emails(None)
            page.update()

        page.on_timer = auto_refresh
        page.timer_interval = 5000  # 5000ms = 5 seconds

    def toggle_server(self, e):
        if self.email_server.is_running():
            logger.info("Stopping email server")
            self.email_server.stop()
            self.status_text.value = "Server Status: Stopped"
            self.status_text.color = "red"
            self.start_button.text = "Start Server"
            self.config_display.content = ft.Column(
                [ft.Text("Server not running", color=ft.Colors.GREY_400)]
            )
            self.port_notification.visible = False

            # Show authentication and TLS settings when server is stopped
            self.username_field.visible = True
            self.password_field.visible = True
            self.tls_switch.visible = True
        else:
            try:
                logger.info("Starting email server")
                # Create new server instance with current settings
                self.email_server = EmailServer(
                    username=self.username_field.value,
                    password=self.password_field.value,
                    use_tls=self.tls_switch.value,
                )
                self.email_server.start()
                self.status_text.value = "Server Status: Running"
                self.status_text.color = "green"
                self.start_button.text = "Stop Server"
                config = self.email_server.get_config()

                # Hide authentication and TLS settings when server is running
                self.username_field.visible = False
                self.password_field.visible = False
                self.tls_switch.visible = False

                # Format configuration display
                config_text = ft.Column(
                    [
                        ft.Text(f"Host: {config['host']}", color=ft.Colors.WHITE),
                        ft.Text(f"Port: {config['port']}", color=ft.Colors.WHITE),
                        ft.Text(
                            f"Authentication: {'Enabled' if config['username'] else 'None'}",
                            color=ft.Colors.WHITE,
                        ),
                        ft.Text(
                            f"TLS: {'Enabled' if config['tls'] else 'Disabled'}",
                            color=ft.Colors.WHITE,
                        ),
                    ]
                )
                self.config_display.content = config_text

                # Show port change notification if port is different from default
                if config["port"] != 1025:
                    self.port_notification.value = (
                        f"Note: Using port {config['port']} as port 1025 was in use"
                    )
                    self.port_notification.visible = True
                    logger.info(f"Using alternative port: {config['port']}")
                else:
                    self.port_notification.visible = False
            except OSError as error:
                logger.error(f"Failed to start server: {str(error)}")
                self.status_text.value = f"Server Error: {str(error)}"
                self.status_text.color = "red"
                self.port_notification.visible = False

        # Update all UI elements
        self.status_text.update()
        self.start_button.update()
        self.config_display.update()
        self.port_notification.update()
        self.username_field.update()
        self.password_field.update()
        self.tls_switch.update()
        self.refresh_emails(e)

    def refresh_emails(self, e):
        if self.email_server.is_running():
            try:
                messages = self.email_server.handler.get_messages()
                logger.info(f"Refreshing email list. Found {len(messages)} messages")

                self.email_list.content.controls.clear()
                for msg in messages:
                    is_read = msg["id"] in self.read_messages
                    self.email_list.content.controls.append(
                        ft.Card(
                            content=ft.Container(
                                content=ft.Row(
                                    [
                                        ft.Icon(
                                            name=(
                                                ft.Icons.MAIL
                                                if is_read
                                                else ft.Icons.MAIL_OUTLINE
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
                                                ),
                                                ft.Text(
                                                    f"Subject: {msg['subject']}",
                                                    color=(
                                                        ft.Colors.BLUE_200
                                                        if is_read
                                                        else ft.Colors.WHITE
                                                    ),
                                                ),
                                                ft.Text(
                                                    f"Date: {msg['date']}",
                                                    color=ft.Colors.GREY_400,
                                                    size=12,
                                                ),
                                            ],
                                            spacing=5,
                                        ),
                                    ],
                                    spacing=10,
                                ),
                                padding=10,
                                on_click=lambda e, m=msg: self.show_email_details(m),
                            ),
                            color=ft.Colors.BLUE_900 if is_read else ft.Colors.BLUE_800,
                        )
                    )
                self.email_list.update()
            except Exception as e:
                logger.error(f"Error refreshing emails: {str(e)}")

    def show_email_details(self, message):
        try:
            self.selected_message = message
            self.read_messages.add(message["id"])  # Mark as read when opened
            self.email_details.content.controls[1].content.value = message["from"]
            self.email_details.content.controls[2].content.value = message["to"]
            self.email_details.content.controls[3].content.value = message["subject"]

            # Handle HTML content
            if message.get("is_html") and message.get("html_content"):
                self.email_details.content.controls[4].content.value = message[
                    "html_content"
                ]
            else:
                self.email_details.content.controls[4].content.value = message["body"]

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
                self.email_server.handler.delete_message(self.selected_message["id"])
                self.close_email_details(e)
                self.refresh_emails(e)
                logger.info(f"Deleted email from {self.selected_message['from']}")
            except Exception as e:
                logger.error(f"Error deleting email: {str(e)}")

    def clear_emails(self, e):
        try:
            self.email_server.handler.clear_messages()
            self.read_messages.clear()  # Clear read status
            self.email_list.content.controls.clear()
            self.email_list.update()
            self.close_email_details(e)
            logger.info("All emails cleared")
        except Exception as e:
            logger.error(f"Error clearing emails: {str(e)}")


def main():
    try:
        logger.info("Starting Email Testing Server application")
        app = EmailTestingApp()
        ft.app(target=app.main)
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        raise


if __name__ == "__main__":
    main()
