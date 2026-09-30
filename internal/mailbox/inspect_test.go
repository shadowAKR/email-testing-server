package mailbox

import (
	"archive/zip"
	"bytes"
	"io"
	"strings"
	"testing"
)

func TestInspect(t *testing.T) {
	m := Message{Raw: "Subject: Code\r\nX-Test: first\r\nX-Test: second\r\n\r\n", Subject: "Your code 123456", HTML: `<html><head><style>.x{color:#123456}</style></head><body><p>Code 123456</p><a href="http://example.test/reset?a=1&amp;b=2">Reset</a><img src="x"><img alt="" src="y"><script>999999</script></body></html>`}
	r := Inspect(m)
	if len(r.Codes) != 1 || r.Codes[0] != "123456" {
		t.Fatalf("unexpected codes: %v", r.Codes)
	}
	if len(r.Links) != 1 || r.Links[0] != "http://example.test/reset?a=1&b=2" {
		t.Fatalf("unexpected links: %v", r.Links)
	}
	if len(r.Warnings) != 4 {
		t.Fatalf("unexpected warnings: %v", r.Warnings)
	}
	if len(r.Headers) != 3 {
		t.Fatalf("lost repeated headers: %v", r.Headers)
	}
}

func TestInlineImageMetadata(t *testing.T) {
	raw := "Content-Type: multipart/related; boundary=x\r\n\r\n--x\r\nContent-Type: text/html\r\n\r\n<img src=\"cid:logo\">\r\n--x\r\nContent-Type: image/png\r\nContent-ID: <logo>\r\nContent-Transfer-Encoding: base64\r\n\r\naGVsbG8=\r\n--x--\r\n"
	m, err := Parse([]byte(raw), "", nil)
	if err != nil {
		t.Fatal(err)
	}
	if len(m.Attachments) != 1 || m.Attachments[0].ContentID != "logo" {
		t.Fatalf("lost content id: %#v", m.Attachments)
	}
	s := New(nil)
	if err := s.Import([]byte(raw)); err != nil {
		t.Fatal(err)
	}
	got, err := s.Get(s.Snapshot().Messages[0].ID)
	if err != nil {
		t.Fatal(err)
	}
	if string(got.Attachments[0].InlineData) != "hello" {
		t.Fatal("inline image data was not made available")
	}
}

func TestImportExportRoundTrip(t *testing.T) {
	s := New(nil)
	raw := "From: test@example.test\r\nTo: dev@example.test\r\nSubject: Saved email\r\n\r\nVerification code 654321"
	if err := s.Import([]byte(raw)); err != nil {
		t.Fatal(err)
	}
	if s.Snapshot().Received != 1 || len(s.Snapshot().Messages) != 1 {
		t.Fatal("import not captured")
	}
	var buf bytes.Buffer
	if err := s.ExportZIP(&buf); err != nil {
		t.Fatal(err)
	}
	z, err := zip.NewReader(bytes.NewReader(buf.Bytes()), int64(buf.Len()))
	if err != nil {
		t.Fatal(err)
	}
	if len(z.File) != 1 || !strings.HasSuffix(z.File[0].Name, ".eml") {
		t.Fatal("missing eml")
	}
	f, err := z.File[0].Open()
	if err != nil {
		t.Fatal(err)
	}
	defer f.Close()
	got, err := io.ReadAll(f)
	if err != nil || string(got) != raw {
		t.Fatal("export changed original bytes")
	}
	restored := New(nil)
	if err := restored.Import(got); err != nil {
		t.Fatal(err)
	}
	if restored.Snapshot().Messages[0].Subject != "Saved email" {
		t.Fatal("round trip lost subject")
	}
	s.storedBytes = MaxStoredBytes
	if err := s.Import([]byte(raw)); err == nil {
		t.Fatal("import bypassed capacity")
	}
	if err := New(nil).Import([]byte("broken header\r\n\r\nbody")); err == nil {
		t.Fatal("invalid import accepted")
	}
}
