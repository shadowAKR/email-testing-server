package mailbox

import (
	"archive/zip"
	"bytes"
	"io"
	"net/mail"
	"regexp"
	"sort"
	"strings"

	"golang.org/x/net/html"
)

type Header struct {
	Name  string `json:"name"`
	Value string `json:"value"`
}
type Inspection struct {
	Headers  []Header `json:"headers"`
	Links    []string `json:"links"`
	Codes    []string `json:"codes"`
	Warnings []string `json:"warnings"`
}

var urlPattern = regexp.MustCompile(`https?://[^\s<>"']+`)
var codePattern = regexp.MustCompile(`\b[0-9]{4,8}\b`)

// Inspect never fetches URLs. Codes are candidates, not verified OTPs.
func Inspect(m Message) Inspection {
	r := Inspection{Headers: []Header{}, Links: []string{}, Codes: []string{}, Warnings: []string{}}
	if parsed, err := mail.ReadMessage(strings.NewReader(m.Raw)); err == nil {
		for name, values := range parsed.Header {
			for _, value := range values {
				r.Headers = append(r.Headers, Header{name, value})
			}
		}
		sort.SliceStable(r.Headers, func(i, j int) bool { return r.Headers[i].Name < r.Headers[j].Name })
	}
	links := map[string]bool{}
	addLink := func(value string) {
		if value != "" && !links[value] {
			links[value] = true
			r.Links = append(r.Links, value)
		}
	}
	for _, value := range urlPattern.FindAllString(m.Text, -1) {
		addLink(strings.TrimRight(value, ".,;!?)"))
	}
	var visible strings.Builder
	missingAlt := 0
	if doc, err := html.Parse(strings.NewReader(m.HTML)); err == nil {
		var walk func(*html.Node)
		walk = func(n *html.Node) {
			if n.Type == html.ElementNode && (n.Data == "script" || n.Data == "style" || n.Data == "head") {
				return
			}
			if n.Type == html.TextNode {
				visible.WriteString(n.Data)
				visible.WriteByte(' ')
			}
			if n.Type == html.ElementNode {
				hasAlt := false
				for _, a := range n.Attr {
					if n.Data == "a" && a.Key == "href" {
						addLink(strings.TrimSpace(a.Val))
					}
					if a.Key == "alt" {
						hasAlt = true
					}
				}
				if n.Data == "img" && !hasAlt {
					missingAlt++
				}
			}
			for c := n.FirstChild; c != nil; c = c.NextSibling {
				walk(c)
			}
		}
		walk(doc)
	}
	seenCodes := map[string]bool{}
	for _, code := range codePattern.FindAllString(m.Subject+" "+m.Text+" "+visible.String(), -1) {
		if !seenCodes[code] {
			seenCodes[code] = true
			r.Codes = append(r.Codes, code)
		}
	}
	if strings.TrimSpace(m.Text) == "" {
		r.Warnings = append(r.Warnings, "No plain-text alternative. Add one for clients that cannot display HTML.")
	}
	if strings.TrimSpace(m.HTML) == "" {
		r.Warnings = append(r.Warnings, "No HTML alternative. Marketing and transactional layouts may need an HTML version.")
	}
	if m.Subject == "(No subject)" {
		r.Warnings = append(r.Warnings, "Missing subject.")
	}
	if parsed, err := mail.ReadMessage(strings.NewReader(m.Raw)); err == nil {
		if parsed.Header.Get("Reply-To") == "" {
			r.Warnings = append(r.Warnings, "No Reply-To header. Replies will go to the From address.")
		}
		if parsed.Header.Get("List-Unsubscribe") == "" && (strings.Contains(strings.ToLower(m.Subject), "newsletter") || strings.Contains(strings.ToLower(m.HTML), "unsubscribe")) {
			r.Warnings = append(r.Warnings, "Consider a List-Unsubscribe header for bulk email.")
		}
	}
	if missingAlt > 0 {
		r.Warnings = append(r.Warnings, "Some images lack an alt attribute. Add descriptive text or an empty alt for decorative images.")
	}
	for _, link := range r.Links {
		if strings.HasPrefix(strings.ToLower(link), "http:") {
			r.Warnings = append(r.Warnings, "Some links use unencrypted HTTP.")
			break
		}
	}
	return r
}

// Import uses the same parser and capacity checks as SMTP delivery.
func (s *Server) Import(raw []byte) error {
	return (&session{server: s}).Data(bytes.NewReader(raw))
}

// ExportZIP holds a read lock so every exported message belongs to one snapshot.
func (s *Server) ExportZIP(w io.Writer) error {
	s.mu.RLock()
	defer s.mu.RUnlock()
	z := zip.NewWriter(w)
	for _, m := range s.messages {
		f, err := z.Create(m.ID + ".eml")
		if err != nil {
			return err
		}
		if _, err = io.WriteString(f, m.Raw); err != nil {
			return err
		}
	}
	return z.Close()
}
