// Package mailbox implements an in-memory SMTP capture server. It never relays mail.
package mailbox

import (
	"bytes"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"mime"
	"net"
	"strconv"
	"strings"
	"sync"
	"time"

	message "github.com/emersion/go-message"
	_ "github.com/emersion/go-message/charset"
	"github.com/emersion/go-message/mail"
	"github.com/emersion/go-smtp"
)

const MaxMessageBytes = 25 << 20
const MaxStoredBytes = 128 << 20
const MaxMessages = 1000

type Attachment struct {
	Name        string `json:"name"`
	ContentType string `json:"contentType"`
	ContentID   string `json:"contentId,omitempty"`
	Size        int    `json:"size"`
	Data        []byte `json:"-"`
	InlineData  []byte `json:"inlineData,omitempty"`
}
type Message struct {
	ID           string       `json:"id"`
	From         string       `json:"from"`
	To           string       `json:"to"`
	Subject      string       `json:"subject"`
	Date         string       `json:"date"`
	ReceivedAt   string       `json:"receivedAt"`
	EnvelopeFrom string       `json:"envelopeFrom"`
	Recipients   []string     `json:"recipients"`
	Text         string       `json:"text"`
	HTML         string       `json:"html"`
	Raw          string       `json:"raw"`
	Read         bool         `json:"read"`
	Size         int          `json:"size"`
	Attachments  []Attachment `json:"attachments"`
}
type Summary struct {
	ID              string `json:"id"`
	From            string `json:"from"`
	To              string `json:"to"`
	Subject         string `json:"subject"`
	Preview         string `json:"preview"`
	ReceivedAt      string `json:"receivedAt"`
	Read            bool   `json:"read"`
	Size            int    `json:"size"`
	AttachmentCount int    `json:"attachmentCount"`
}
type State struct {
	Running  bool      `json:"running"`
	Host     string    `json:"host"`
	Port     int       `json:"port"`
	Received uint64    `json:"received"`
	Unread   int       `json:"unread"`
	Messages []Summary `json:"messages"`
}
type Server struct {
	lifecycle   sync.Mutex
	mu          sync.RWMutex
	smtp        *smtp.Server
	listener    net.Listener
	host        string
	port        int
	messages    []*Message
	storedBytes int
	received    uint64
	changed     func()
}

func New(changed func()) *Server { return &Server{host: "127.0.0.1", port: 1025, changed: changed} }
func (s *Server) notify() {
	if s.changed != nil {
		s.changed()
	}
}
func (s *Server) Start(host string, port int) error {
	s.lifecycle.Lock()
	defer s.lifecycle.Unlock()
	s.mu.RLock()
	running := s.smtp != nil
	s.mu.RUnlock()
	if running {
		return errors.New("SMTP server is already running")
	}
	host = strings.TrimSpace(host)
	if host == "" || port < 0 || port > 65535 {
		return errors.New("provide a host and a port between 1 and 65535")
	}
	listener, err := net.Listen("tcp", net.JoinHostPort(host, strconv.Itoa(port)))
	if err != nil {
		return fmt.Errorf("cannot listen on %s:%d: %w", host, port, err)
	}
	server := smtp.NewServer(s)
	server.Domain = "localhost"
	server.MaxMessageBytes = MaxMessageBytes
	server.MaxRecipients = 100
	server.ReadTimeout = 30 * time.Second
	server.WriteTimeout = 30 * time.Second
	s.mu.Lock()
	s.smtp = server
	s.listener = listener
	s.host = host
	s.port = listener.Addr().(*net.TCPAddr).Port
	s.mu.Unlock()
	go func() {
		defer listener.Close()
		_ = server.Serve(listener)
		s.mu.Lock()
		if s.smtp == server {
			s.smtp = nil
		}
		s.mu.Unlock()
		s.notify()
	}()
	s.notify()
	return nil
}
func (s *Server) Stop() error {
	s.lifecycle.Lock()
	defer s.lifecycle.Unlock()
	s.mu.Lock()
	server := s.smtp
	listener := s.listener
	s.smtp = nil
	s.listener = nil
	s.mu.Unlock()
	if server == nil {
		return nil
	}
	err := server.Close()
	// Close our listener too: Stop may run before Serve registers it.
	if listener != nil {
		_ = listener.Close()
	}
	if errors.Is(err, net.ErrClosed) {
		err = nil
	}
	s.notify()
	return err
}
func (s *Server) NewSession(_ *smtp.Conn) (smtp.Session, error) { return &session{server: s}, nil }

type session struct {
	server *Server
	from   string
	to     []string
}

func (s *session) Reset()                                      { s.from = ""; s.to = nil }
func (s *session) Logout() error                               { return nil }
func (s *session) Mail(from string, _ *smtp.MailOptions) error { s.from = from; return nil }
func (s *session) Rcpt(to string, _ *smtp.RcptOptions) error   { s.to = append(s.to, to); return nil }
func (s *session) Data(r io.Reader) error {
	raw, err := io.ReadAll(io.LimitReader(r, MaxMessageBytes+1))
	if err != nil {
		return err
	}
	if len(raw) > MaxMessageBytes {
		return &smtp.SMTPError{Code: 552, Message: "Message exceeds 25 MiB"}
	}
	msg, err := Parse(raw, s.from, s.to)
	if err != nil {
		return &smtp.SMTPError{Code: 554, Message: "Invalid MIME message: " + err.Error()}
	}
	s.server.mu.Lock()
	if len(s.server.messages) >= MaxMessages || s.server.storedBytes+msg.Size > MaxStoredBytes {
		s.server.mu.Unlock()
		return &smtp.SMTPError{Code: 452, Message: "Inbox full. Delete captured messages and retry."}
	}
	s.server.messages = append([]*Message{msg}, s.server.messages...)
	s.server.storedBytes += msg.Size
	s.server.received++
	s.server.mu.Unlock()
	s.server.notify()
	return nil
}
func Parse(raw []byte, from string, to []string) (*Message, error) {
	reader, err := mail.CreateReader(bytes.NewReader(raw))
	if err != nil && !message.IsUnknownCharset(err) {
		return nil, err
	}
	defer reader.Close()
	id := make([]byte, 16)
	if _, err = rand.Read(id); err != nil {
		return nil, err
	}
	subject, _ := reader.Header.Subject()
	fromHeader, _ := reader.Header.Text("From")
	toHeader, _ := reader.Header.Text("To")
	msg := &Message{ID: hex.EncodeToString(id), From: fromHeader, To: toHeader, Subject: subject, Date: reader.Header.Get("Date"), ReceivedAt: time.Now().Format(time.RFC3339Nano), EnvelopeFrom: from, Recipients: append([]string{}, to...), Raw: string(raw), Size: len(raw), Attachments: []Attachment{}}
	if msg.From == "" {
		msg.From = from
	}
	if msg.To == "" {
		msg.To = strings.Join(to, ", ")
	}
	if msg.Subject == "" {
		msg.Subject = "(No subject)"
	}
	for {
		part, err := reader.NextPart()
		if err == io.EOF {
			break
		}
		if err != nil && !message.IsUnknownCharset(err) {
			return nil, err
		}
		body, err := io.ReadAll(part.Body)
		if err != nil {
			return nil, err
		}
		ct, params, _ := mime.ParseMediaType(part.Header.Get("Content-Type"))
		disposition, dp, _ := mime.ParseMediaType(part.Header.Get("Content-Disposition"))
		name := dp["filename"]
		if name == "" {
			name = params["name"]
		}
		contentID := strings.Trim(strings.TrimSpace(part.Header.Get("Content-ID")), "<>")
		if name != "" || disposition == "attachment" || (ct != "text/plain" && ct != "text/html" && ct != "") {
			if name == "" {
				name = contentID
				if name == "" {
					name = "attachment"
				}
			}
			msg.Attachments = append(msg.Attachments, Attachment{Name: name, ContentType: ct, ContentID: contentID, Size: len(body), Data: body})
		} else if ct == "text/html" {
			msg.HTML += string(body)
		} else {
			msg.Text += string(body)
		}
	}
	return msg, nil
}
func (s *Server) Snapshot() State {
	s.mu.RLock()
	defer s.mu.RUnlock()
	state := State{Running: s.smtp != nil, Host: s.host, Port: s.port, Received: s.received, Messages: []Summary{}}
	for _, m := range s.messages {
		preview := strings.Join(strings.Fields(m.Text), " ")
		runes := []rune(preview)
		if len(runes) > 120 {
			preview = string(runes[:120]) + "…"
		}
		if preview == "" && m.HTML != "" {
			preview = "HTML message"
		}
		state.Messages = append(state.Messages, Summary{m.ID, m.From, m.To, m.Subject, preview, m.ReceivedAt, m.Read, m.Size, len(m.Attachments)})
		if !m.Read {
			state.Unread++
		}
	}
	return state
}
func (s *Server) Get(id string) (Message, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	for _, m := range s.messages {
		if m.ID == id {
			copy := *m
			copy.Recipients = append([]string{}, m.Recipients...)
			copy.Attachments = append([]Attachment{}, m.Attachments...)
			for i := range copy.Attachments {
				copy.Attachments[i].Data = append([]byte{}, copy.Attachments[i].Data...)
				// Only expose inline image bytes to the desktop preview. Other attachment
				// data stays behind the explicit SaveAttachment action.
				if copy.Attachments[i].ContentID != "" && strings.HasPrefix(strings.ToLower(copy.Attachments[i].ContentType), "image/") {
					copy.Attachments[i].InlineData = append([]byte{}, copy.Attachments[i].Data...)
				}
			}
			return copy, nil
		}
	}
	return Message{}, errors.New("message no longer exists")
}
func (s *Server) SetRead(id string, read bool) error {
	s.mu.Lock()
	found := false
	for _, m := range s.messages {
		if m.ID == id {
			m.Read = read
			found = true
			break
		}
	}
	s.mu.Unlock()
	if !found {
		return errors.New("message no longer exists")
	}
	s.notify()
	return nil
}
func (s *Server) Delete(id string) error {
	s.mu.Lock()
	found := false
	for i, m := range s.messages {
		if m.ID == id {
			s.storedBytes -= m.Size
			s.messages = append(s.messages[:i], s.messages[i+1:]...)
			found = true
			break
		}
	}
	s.mu.Unlock()
	if !found {
		return errors.New("message no longer exists")
	}
	s.notify()
	return nil
}
func (s *Server) Clear() { s.mu.Lock(); s.messages = nil; s.storedBytes = 0; s.mu.Unlock(); s.notify() }
