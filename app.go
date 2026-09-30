package main

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"io"
	"net"
	"net/smtp"
	"net/url"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync/atomic"
	"time"

	"github.com/wailsapp/wails/v2/pkg/runtime"
	"postroom/internal/mailbox"
)

type App struct {
	ctx     context.Context
	server  *mailbox.Server
	closing atomic.Bool
}

func NewApp() *App { return &App{} }
func (a *App) startup(ctx context.Context) {
	a.ctx = ctx
	a.server = mailbox.New(func() {
		if !a.closing.Load() {
			runtime.EventsEmit(ctx, "mailbox:changed")
		}
	})
}
func (a *App) shutdown(_ context.Context) {
	a.closing.Store(true)
	if a.server != nil {
		_ = a.server.Stop()
	}
}
func (a *App) GetState() mailbox.State { return a.server.Snapshot() }
func (a *App) StartServer(host string, port int) error {
	if port < 1 || port > 65535 {
		return errors.New("port must be between 1 and 65535")
	}
	return a.server.Start(host, port)
}
func (a *App) StopServer() error                             { return a.server.Stop() }
func (a *App) GetMessage(id string) (mailbox.Message, error) { return a.server.Get(id) }
func (a *App) SetRead(id string, read bool) error            { return a.server.SetRead(id, read) }
func (a *App) DeleteMessage(id string) error                 { return a.server.Delete(id) }
func (a *App) ClearMessages()                                { a.server.Clear() }
func (a *App) SaveAttachment(id string, index int) (bool, error) {
	m, err := a.server.Get(id)
	if err != nil {
		return false, err
	}
	if index < 0 || index >= len(m.Attachments) {
		return false, errors.New("attachment not found")
	}
	attachment := m.Attachments[index]
	name := filepath.Base(strings.ReplaceAll(attachment.Name, "\\", "/"))
	return a.save(name, attachment.Data)
}
func (a *App) ExportMessage(id string) (bool, error) {
	m, err := a.server.Get(id)
	if err != nil {
		return false, err
	}
	return a.save("message-"+m.ID[:8]+".eml", []byte(m.Raw))
}
func (a *App) save(name string, data []byte) (bool, error) {
	path, err := runtime.SaveFileDialog(a.ctx, runtime.SaveDialogOptions{Title: "Save captured email", DefaultFilename: name, CanCreateDirectories: true})
	if err != nil || path == "" {
		return false, err
	}
	if err = os.WriteFile(path, data, 0600); err != nil {
		return false, err
	}
	return true, nil
}

// SendTestMessage exercises the real SMTP listener, including MIME parsing.
func (a *App) SendTestMessage() error {
	state := a.server.Snapshot()
	if !state.Running {
		return errors.New("start the SMTP server first")
	}
	host := state.Host
	if host == "0.0.0.0" || host == "::" {
		host = "localhost"
	}
	conn, err := net.DialTimeout("tcp", net.JoinHostPort(host, strconv.Itoa(state.Port)), 3*time.Second)
	if err != nil {
		return err
	}
	defer conn.Close()
	_ = conn.SetDeadline(time.Now().Add(5 * time.Second))
	client, err := smtp.NewClient(conn, "localhost")
	if err != nil {
		return err
	}
	defer client.Close()
	if err = client.Mail("hello@example.test"); err != nil {
		return err
	}
	if err = client.Rcpt("developer@localhost"); err != nil {
		return err
	}
	writer, err := client.Data()
	if err != nil {
		return err
	}
	_, err = fmt.Fprintf(writer, "From: Postroom <hello@example.test>\r\nTo: Developer <developer@localhost>\r\nSubject: Your inbox is ready ✨\r\nDate: %s\r\nMIME-Version: 1.0\r\nContent-Type: multipart/alternative; boundary=postroom-demo\r\n\r\n--postroom-demo\r\nContent-Type: text/plain; charset=utf-8\r\n\r\nHello, developer!\r\nYour SMTP connection is working. Point your application at %s:%d to capture your next email.\r\nEverything stays on this machine. Happy building!\r\n--postroom-demo\r\nContent-Type: text/html; charset=utf-8\r\n\r\n<div style=\"font-family:Arial,sans-serif;background:#f4f6fa;padding:48px;color:#182331\"><div style=\"max-width:500px;margin:auto;background:white;border-radius:16px;padding:40px\"><p style=\"color:#6557d9;font-weight:bold;letter-spacing:3px\">POSTROOM</p><h1>Your inbox is ready ✨</h1><p style=\"line-height:1.8;color:#657084\">Hello, developer! Your SMTP connection is working. You're all set to test your next great idea.</p><div style=\"background:#f0edff;padding:20px;border-radius:10px;color:#6557d9\">Captured locally. Ready to inspect.</div><p style=\"color:#8892a3;font-size:12px;margin-top:32px\">Sent by Postroom</p></div></div>\r\n--postroom-demo--\r\n", time.Now().Format(time.RFC1123Z), state.Host, state.Port)
	if err != nil {
		return err
	}
	if err = writer.Close(); err != nil {
		return err
	}
	return client.Quit()
}

func (a *App) InspectMessage(id string) (mailbox.Inspection, error) {
	m, err := a.server.Get(id)
	if err != nil {
		return mailbox.Inspection{}, err
	}
	return mailbox.Inspect(m), nil
}
func (a *App) ImportMessage() (bool, error) {
	path, err := runtime.OpenFileDialog(a.ctx, runtime.OpenDialogOptions{Title: "Import email", Filters: []runtime.FileFilter{{DisplayName: "Email (.eml)", Pattern: "*.eml"}}})
	if err != nil || path == "" {
		return false, err
	}
	f, err := os.Open(path)
	if err != nil {
		return false, err
	}
	defer f.Close()
	raw, err := io.ReadAll(io.LimitReader(f, mailbox.MaxMessageBytes+1))
	if err != nil {
		return false, err
	}
	if err = a.server.Import(raw); err != nil {
		return false, err
	}
	return true, nil
}
func (a *App) ExportInbox() (bool, error) {
	var data bytes.Buffer
	if err := a.server.ExportZIP(&data); err != nil {
		return false, err
	}
	return a.save("postroom-inbox.zip", data.Bytes())
}

// Override with -ldflags '-X main.contributeURL=https://…' for a sponsored build.
var contributeURL = "https://github.com/shadowAKR/email-testing-server"

func (a *App) OpenContribute() error {
	u, err := url.Parse(contributeURL)
	if err != nil || u.Scheme != "https" || u.Hostname() == "" || u.User != nil {
		return errors.New("contribution URL must be a valid HTTPS URL")
	}
	runtime.BrowserOpenURL(a.ctx, u.String())
	return nil
}
