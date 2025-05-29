# Email Testing Server

A local email testing server with a modern GUI built using Flet. This application allows you to test email functionality locally by providing a simple SMTP server and a user-friendly interface to view, manage, and test emails.

## Features

- Start/stop local SMTP server
- View incoming emails in real-time
- Support for HTML emails and emojis
- Mark emails as read/unread
- Delete individual emails
- Clear all emails
- Auto-refresh email list
- Modern dark theme UI

## Installation

### Windows

1. Download the latest `EmailTestingServer-Setup.exe` from the releases
2. Run the installer and follow the on-screen instructions
3. The application will be installed in the Program Files directory
4. Shortcuts will be created on the desktop and start menu

### Ubuntu/Debian

1. Download the latest `.deb` package from the releases
2. Install using:
   ```bash
   sudo dpkg -i email-testing-server_1.0.0_amd64.deb
   ```
3. If you encounter any dependency issues, run:
   ```bash
   sudo apt-get install -f
   ```

## Building from Source

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/email-testing-server.git
   cd email-testing-server
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the build script:
   ```bash
   python build.py
   ```

4. The installable packages will be created in the `dist` directory

## Usage

1. Launch the application
2. Click "Start Server" to start the local SMTP server
3. Configure your email client to use:
   - SMTP Server: localhost
   - Port: 1025 (or the port shown in the application)
   - No authentication required
4. Send test emails to any address
5. View received emails in the application
6. Click on an email to view its details
7. Use the delete button to remove individual emails
8. Use the clear button to remove all emails

## Requirements

- Python 3.7 or higher
- Flet 0.28.0 or higher
- aiosmtpd 1.4.4 or higher
- html2text 2020.1.16 or higher
- emoji 2.8.0 or higher

## License

This project is licensed under the MIT License - see the LICENSE file for details. 