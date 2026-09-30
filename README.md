# Postroom

A local SMTP capture desktop app rewritten in **Go + Wails v2**, with a React/TypeScript interface. Point your application's email settings at the local listener, send an email, and inspect it without delivering anything to real recipients.

## Features

- Start and stop a real SMTP server (default `127.0.0.1:1025`).
- Live inbox updates, sender/recipient/subject/preview search, unread and attachment filters.
- Unicode headers, nested MIME, HTML, plain text, and encoded attachments.
- Sandboxed HTML previews with scripts, external resources, and navigation disabled.
- Inline CID image rendering in sandboxed HTML previews; remote resources remain blocked.
- Raw message inspection, `.eml` export, and native attachment save dialogs.
- Read/unread controls, individual deletion, and confirmed inbox clearing.
- Configurable listen address, clear port-conflict errors, and a built-in SMTP test email.
- Full-height three-pane inbox, sidebar server controls, and a dedicated Attachments tab with filenames, types, sizes, and save actions.
- Dark, responsive desktop interface; no external fonts or UI services.
- A visible **Contribute** action that can be pointed at a project, sponsor, or donation page during builds.

Messages and settings are session-only. Closing the app clears the inbox. Export messages to keep them. The listener does not relay, authenticate, or negotiate TLS. Keep the default loopback address unless you intend to expose capture to your network.

## Prerequisites

- Go **1.27.1+** (matches `go.mod`)
- Node.js **20.19+** or Node.js 22+, and npm
- Platform prerequisites from the [Wails installation guide](https://wails.io/docs/gettingstarted/installation/)

For recent Ubuntu/Debian with WebKitGTK 4.1:

```sh
sudo apt install build-essential pkg-config libgtk-3-dev libwebkit2gtk-4.1-dev
```

If installing system packages is unavailable (for example, in a restricted
container), `make build` downloads the required development metadata and
linker symlinks into an ignored `.native-deps/` cache. The WebKitGTK and GTK
runtime libraries must still be installed on the host.

Windows needs the WebView2 runtime and a working Go/Node toolchain. macOS needs Xcode command-line tools. Build on the target operating system; native Linux builds are not Windows/macOS packages.

## Develop

```sh
go run github.com/wailsapp/wails/v2/cmd/wails@v2.16.0 dev -tags webkit2_41
```

On Windows/macOS omit `-tags webkit2_41`. Wails installs frontend dependencies and runs the Vite dev server automatically. The Go application provides all SMTP and file operations through Wails bindings; there is no Python runtime or separate HTTP API.

## Build

```sh
# Linux using WebKitGTK 4.1
make build
# Equivalent command:
go run github.com/wailsapp/wails/v2/cmd/wails@v2.16.0 build -tags webkit2_41

# Windows or macOS
go run github.com/wailsapp/wails/v2/cmd/wails@v2.16.0 build
```

The Linux executable is `build/bin/postroom`. Windows produces `build/bin/postroom.exe`; macOS produces an application bundle. The compiled frontend is embedded in the executable. Linux users also need GTK3 and WebKitGTK 4.1 runtime libraries.

Run `make package-deb` to build a Debian package in `build/bin/`, or `./scripts/package-deb.sh` to package an existing build. Build on the oldest Linux distribution you intend to support: the native executable links against the build host's system libraries.

`InnoScript.iss` packages the Windows executable with Inno Setup. `snap/snapcraft.yaml` packages an already-built Linux binary; run `make build` first, then `snapcraft`. Packaging requires the corresponding platform tools and is separate from compiling the app.

## Use

1. Launch the executable and click **Start server**.
2. Set your application's SMTP host to `127.0.0.1`, port to `1025`, authentication to none, and TLS/SSL to disabled.
3. Send a message to any address, or click **Send test email**.
4. Select a captured message to preview it, inspect its raw source, or save attachments.

Change host and port through **Server settings** while stopped. If a port is occupied, the app reports the error instead of silently changing your SMTP configuration. HTML previews intentionally block remote images and links but safely render embedded CID images. Attachments remain downloadable.

Limits: 25 MiB per message, 100 recipients per transaction, 1,000 captured messages, and 128 MiB of raw captured mail per session. A full inbox rejects new mail until messages are deleted. Decoded MIME and UI copies use additional memory.

## Verify

```sh
make test
# Backend only (no desktop libraries required):
go test -race ./internal/...
# After a frontend build, validate all Go packages on Linux:
go test -tags webkit2_41 ./...
go vet -tags webkit2_41 ./...
```

The backend tests exercise a real TCP SMTP listener, concurrent delivery, stop/restart, port conflicts, nested MIME, Unicode and legacy charsets, attachment integrity, read/unread state, deletion, and limits. `npm run build` checks TypeScript and builds production assets. `npm run dev` alone previews the frontend but needs a Wails session for backend operations.

## Support and commercial roadmap

The core app is intended to remain free and local-first. The **Contribute** sidebar button opens the project URL by default; distributors can replace it with an HTTPS sponsorship or donation URL at build time:

```sh
go build -ldflags "-X main.contributeURL=https://github.com/sponsors/YOUR_ACCOUNT"
```

See [MONETIZATION.md](MONETIZATION.md) for a feature-prioritized plan that keeps local development free while monetizing team, CI, and hosted analysis features.

## Layout

- `main.go`, `app.go`: Wails lifecycle and desktop bindings.
- `internal/mailbox/`: SMTP server, MIME parsing, synchronized inbox, and tests.
- `frontend/src/`: React/TypeScript interface and local styles.
- `wails.json`, `Makefile`, `build/`: desktop build configuration.
