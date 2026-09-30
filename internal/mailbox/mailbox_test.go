package mailbox

import (
	"fmt"
	"net"
	"net/smtp"
	"strconv"
	"strings"
	"sync"
	"testing"
	"time"
)

const multipartMessage = "From: =?UTF-8?B?Sm9zw6k=?= <sender@example.test>\r\nTo: receiver@example.test\r\nSubject: =?UTF-8?B?SGVsbG8g8J+Riw==?=\r\nMIME-Version: 1.0\r\nContent-Type: multipart/mixed; boundary=outer\r\n\r\n--outer\r\nContent-Type: multipart/alternative; boundary=inner\r\n\r\n--inner\r\nContent-Type: text/plain; charset=iso-8859-1\r\nContent-Transfer-Encoding: quoted-printable\r\n\r\nCaf=E9\r\n--inner\r\nContent-Type: text/html; charset=utf-8\r\n\r\n<h1>Hello 👋</h1>\r\n--inner--\r\n--outer\r\nContent-Type: text/plain; name=notes.txt\r\nContent-Disposition: attachment; filename=notes.txt\r\nContent-Transfer-Encoding: base64\r\n\r\naGVsbG8=\r\n--outer--\r\n"

func TestMIMEParsing(t *testing.T) {
	m, err := Parse([]byte(multipartMessage), "bounce@example.test", []string{"hidden@example.test"})
	if err != nil {
		t.Fatal(err)
	}
	if m.Subject != "Hello 👋" || !strings.Contains(m.From, "José") || strings.TrimSpace(m.Text) != "Café" || m.HTML != "<h1>Hello 👋</h1>" {
		t.Fatalf("incorrect decoded content: %#v", m)
	}
	if len(m.Attachments) != 1 || m.Attachments[0].Name != "notes.txt" || string(m.Attachments[0].Data) != "hello" {
		t.Fatalf("incorrect attachments: %#v", m.Attachments)
	}
	if m.Raw != multipartMessage || m.Recipients[0] != "hidden@example.test" {
		t.Fatal("raw source or SMTP envelope lost")
	}
}
func send(address string) error {
	return smtp.SendMail(address, nil, "sender@example.test", []string{"receiver@example.test"}, []byte(multipartMessage))
}
func startServer(t *testing.T) *Server {
	t.Helper()
	s := New(nil)
	if err := s.Start("127.0.0.1", 0); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = s.Stop() })
	return s
}
func address(s *Server) string {
	state := s.Snapshot()
	return net.JoinHostPort(state.Host, strconv.Itoa(state.Port))
}
func TestSMTPAndInboxLifecycle(t *testing.T) {
	s := startServer(t)
	addr := address(s)
	if err := send(addr); err != nil {
		t.Fatal(err)
	}
	state := s.Snapshot()
	if len(state.Messages) != 1 || state.Unread != 1 || state.Received != 1 {
		t.Fatalf("unexpected state: %#v", state)
	}
	id := state.Messages[0].ID
	if err := s.SetRead(id, true); err != nil {
		t.Fatal(err)
	}
	if s.Snapshot().Unread != 0 {
		t.Fatal("read state not applied")
	}
	if err := s.SetRead(id, false); err != nil {
		t.Fatal(err)
	}
	if s.Snapshot().Unread != 1 {
		t.Fatal("unread state not applied")
	}
	copy, err := s.Get(id)
	if err != nil {
		t.Fatal(err)
	}
	copy.Attachments[0].Data[0] = 'X'
	original, _ := s.Get(id)
	if string(original.Attachments[0].Data) != "hello" {
		t.Fatal("mutable data escaped store")
	}
	if err := s.Delete(id); err != nil {
		t.Fatal(err)
	}
	if _, err := s.Get(id); err == nil {
		t.Fatal("deleted message still exists")
	}
	if err := send(addr); err != nil {
		t.Fatal(err)
	}
	s.Clear()
	if len(s.Snapshot().Messages) != 0 || s.storedBytes != 0 {
		t.Fatal("clear did not reset storage")
	}
	if err := s.Stop(); err != nil {
		t.Fatal(err)
	}
	if s.Snapshot().Running {
		t.Fatal("still running")
	}
	if err := s.Start("127.0.0.1", 0); err != nil {
		t.Fatal(err)
	}
	if err := send(address(s)); err != nil {
		t.Fatal(err)
	}
}
func TestPortConflict(t *testing.T) {
	s := startServer(t)
	other := New(nil)
	defer other.Stop()
	if err := other.Start("127.0.0.1", s.Snapshot().Port); err == nil {
		t.Fatal("port conflict silently accepted")
	}
	if other.Snapshot().Running {
		t.Fatal("failed server claims to run")
	}
}
func TestConcurrentCapture(t *testing.T) {
	s := startServer(t)
	addr := address(s)
	var wg sync.WaitGroup
	for i := 0; i < 12; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			if err := send(addr); err != nil {
				t.Error(err)
			}
			_ = s.Snapshot()
		}()
	}
	wg.Wait()
	state := s.Snapshot()
	if len(state.Messages) != 12 || state.Received != 12 {
		t.Fatalf("lost messages: %d", len(state.Messages))
	}
	ids := map[string]bool{}
	for _, m := range state.Messages {
		if ids[m.ID] {
			t.Fatal("duplicate ID")
		}
		ids[m.ID] = true
	}
}
func TestLimitsAndMalformedMessage(t *testing.T) {
	s := New(nil)
	sess := &session{server: s}
	if err := sess.Data(strings.NewReader("not a MIME header\r\n\r\nbody")); err == nil {
		t.Fatal("invalid message accepted")
	}
	if err := sess.Data(strings.NewReader(strings.Repeat("x", MaxMessageBytes+1))); err == nil {
		t.Fatal("oversized message accepted")
	}
	s.storedBytes = MaxStoredBytes
	if err := sess.Data(strings.NewReader("Subject: full\r\n\r\ntest")); err == nil {
		t.Fatal("full inbox accepted message")
	}
	if len(s.Snapshot().Messages) != 0 {
		t.Fatal("rejected mail stored")
	}
}
func TestImmediateStopAndRestart(t *testing.T) {
	s := New(nil)
	defer s.Stop()
	for i := 0; i < 20; i++ {
		if err := s.Start("127.0.0.1", 0); err != nil {
			t.Fatal(err)
		}
		addr := address(s)
		if err := s.Stop(); err != nil {
			t.Fatal(err)
		}
		if conn, err := net.DialTimeout("tcp", addr, 100*time.Millisecond); err == nil {
			conn.Close()
			t.Fatal("stopped listener still accepts connections")
		}
	}
	if err := s.Start("127.0.0.1", 0); err != nil {
		t.Fatal(err)
	}
	if err := send(address(s)); err != nil {
		t.Fatal(fmt.Errorf("after rapid restart: %w", err))
	}
}
