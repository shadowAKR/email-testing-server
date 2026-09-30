import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowDownToLine,
  ArrowUpRight,
  Check,
  Code2,
  Copy,
  FileText,
  Inbox,
  Mail,
  MailOpen,
  Monitor,
  Paperclip,
  Play,
  Plus,
  Search,
  Settings2,
  ShieldCheck,
  Smartphone,
  Square,
  Tablet,
  Terminal,
  Trash2,
  X,
} from "lucide-react";
import DOMPurify from "dompurify";
import { api, type Message, type State, type Inspection } from "./api";
import "./style.css";

const initial: State = {
  running: false,
  host: "127.0.0.1",
  port: 1025,
  received: 0,
  unread: 0,
  messages: [],
};
const size = (n: number) =>
  n < 1024
    ? `${n} B`
    : n < 1048576
      ? `${(n / 1024).toFixed(1)} KB`
      : `${(n / 1048576).toFixed(1)} MB`;
const sender = (s: string) =>
  s.replace(/<.*>/, "").replaceAll('"', "").trim() || s;
const time = (s: string) =>
  new Date(s).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
function safeDocument(html: string, attachments: Message["attachments"]) {
  const inlineImages = new Map(
    attachments
      .filter((attachment) => attachment.contentId && attachment.inlineData && /^image\//i.test(attachment.contentType))
      .map((attachment) => [
        attachment.contentId!.replace(/^<|>$/g, "").toLowerCase(),
        `data:${attachment.contentType};base64,${attachment.inlineData!}`,
      ]),
  );
  const withInlineImages = html.replace(/\bsrc\s*=\s*(["'])cid:([^"']+)\1/gi, (_, quote, id) => {
    const source = inlineImages.get(String(id).replace(/^<|>$/g, "").toLowerCase());
    return source ? `src=${quote}${source}${quote}` : "";
  });
  const clean = DOMPurify.sanitize(withInlineImages, {
    WHOLE_DOCUMENT: true,
    FORBID_TAGS: [
      "script",
      "iframe",
      "object",
      "embed",
      "form",
      "input",
      "button",
      "textarea",
      "select",
      "meta",
      "base",
      "link",
    ],
    FORBID_ATTR: [
      "srcset",
      "action",
      "formaction",
      "href",
      "xlink:href",
      "target",
    ],
  });
  return `<!doctype html><html><head><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; font-src 'none'; form-action 'none'; base-uri 'none'"><style>body{margin:0;color:#182331;background:#fff;font-family:Arial,sans-serif;overflow-wrap:anywhere}img{max-width:100%}a{pointer-events:none}</style></head><body>${clean}</body></html>`;
}
function App() {
  const [state, setState] = useState<State>(initial);
  const [selected, setSelected] = useState<Message | null>(null);
  const selectedID = useRef<string | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<"all" | "unread" | "attachments">("all");
  const [tab, setTab] = useState<"preview" | "text" | "source" | "attachments" | "inspect">(
    "preview",
  );
  const [modal, setModal] = useState<"settings" | "help" | "clear" | null>(
    null,
  );
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [device, setDevice] = useState("desktop");
  const [host, setHost] = useState("127.0.0.1");
  const [port, setPort] = useState("1025");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const refreshVersion = useRef(0);
  const refresh = useCallback(async () => {
    const version = ++refreshVersion.current;
    const data = await api.GetState();
    if (version !== refreshVersion.current) return;
    setState(data);
    if (
      selectedID.current &&
      !data.messages.some((m) => m.id === selectedID.current)
    ) {
      selectedID.current = null;
      setSelected(null);
    }
  }, []);
  useEffect(() => {
    refresh().catch((e) => setError(String(e)));
    const off = window.runtime?.EventsOn("mailbox:changed", () => {
      refresh().catch((e) => setError(String(e)));
    });
    return () => off?.();
  }, [refresh]);
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(""), 3500);
    return () => clearTimeout(timer);
  }, [toast]);
  const run = async (action: () => Promise<unknown>) => {
    setBusy(true);
    setError("");
    try {
      await action();
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };
  const open = async (id: string) => {
    selectedID.current = id;
    setSelected(null);
    setInspection(null);
    setTab("preview");
    setError("");
    try {
      const [m, details] = await Promise.all([api.GetMessage(id), api.InspectMessage(id)]);
      if (selectedID.current !== id) return;
      setSelected({ ...m, read: true });
      setInspection(details);
      await api.SetRead(id, true);
      await refresh();
    } catch (e) {
      setError(String(e));
    }
  };
  const messages = useMemo(
    () =>
      state.messages.filter(
        (m) =>
          (filter !== "unread" || !m.read) &&
          (filter !== "attachments" || m.attachmentCount > 0) &&
          `${m.from} ${m.to} ${m.subject} ${m.preview}`
            .toLowerCase()
            .includes(query.toLowerCase()),
      ),
    [state.messages, filter, query],
  );
  const preview = useMemo(
    () => (selected?.html ? safeDocument(selected.html, selected.attachments) : ""),
    [selected?.html, selected?.attachments],
  );
  const copy = async (value: string) => {
    try {
      await navigator.clipboard.writeText(value);
      setToast("Copied to clipboard");
    } catch {
      setError(
        "Clipboard access is unavailable. Select and copy the connection details manually.",
      );
    }
  };
  const toggleRead = () =>
    run(async () => {
      if (!selected) return;
      const read = !selected.read;
      await api.SetRead(selected.id, read);
      setSelected({ ...selected, read });
    });
  const save = () =>
    run(async () => {
      if (selected && (await api.ExportMessage(selected.id)))
        setToast("Email exported");
    });
  const start = () =>
    run(async () => {
      await api.StartServer(host, Number(port));
      setToast("SMTP server is listening");
    });
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-icon">
            <Mail size={23} />
          </span>
          <div>
            Postroom<span>LOCAL SMTP SANDBOX</span>
          </div>
        </div>
        <div className="workspace-label">MAILBOX</div>
        <nav aria-label="Mailbox folders">
          <button
            className={filter === "all" ? "nav-item active" : "nav-item"}
            onClick={() => setFilter("all")}
          >
            <Inbox size={18} />
            All messages<span>{state.messages.length}</span>
          </button>
          <button
            className={filter === "unread" ? "nav-item active" : "nav-item"}
            onClick={() => setFilter("unread")}
          >
            <Mail size={18} />
            Unread<span>{state.unread}</span>
          </button>
          <button
            className={
              filter === "attachments" ? "nav-item active" : "nav-item"
            }
            onClick={() => setFilter("attachments")}
          >
            <Paperclip size={18} />
            With attachments
          </button>
        </nav>
        <div className="sidebar-divider" />
        <button className="nav-item" onClick={() => setModal("settings")}>
          <Settings2 size={18} />
          Server settings
        </button>
        <button className="nav-item" onClick={() => setModal("help")}>
          <Code2 size={18} />
          Connection guide
          <ArrowUpRight size={14} />
        </button>
        <button className="nav-item" disabled={busy} onClick={() => run(async () => {
          if (await api.ImportMessage()) setToast("Email imported");
        })}><Plus size={18} />Import .eml</button>
        <button className="nav-item" disabled={busy || !state.messages.length} onClick={() => run(async () => {
          if (await api.ExportInbox()) setToast("Inbox exported");
        })}><ArrowDownToLine size={18} />Export inbox ZIP</button>
        <button className="nav-item" disabled={busy} onClick={() => run(() => api.OpenContribute())}>
          <ArrowUpRight size={18} />Contribute
        </button>
        <section className="sidebar-server" aria-label="SMTP server status">
          <div className="sidebar-server-heading">
            <strong>SMTP server</strong>
            <span className={"status " + (state.running ? "online" : "")}>
              <i />
              {state.running ? "Listening" : "Stopped"}
            </span>
          </div>
          <button
            className="sidebar-address"
            title="Copy SMTP address"
            onClick={() =>
              copy(
                state.running
                  ? `${state.host}:${state.port}`
                  : `${host}:${port}`,
              )
            }
          >
            <code>
              {state.running ? state.host : host}:
              {state.running ? state.port : port}
            </code>
            <Copy size={14} />
          </button>
          <p>No authentication · No TLS</p>
          <button
            className={"button " + (state.running ? "secondary" : "primary")}
            disabled={busy}
            onClick={() =>
              state.running ? run(() => api.StopServer()) : start()
            }
          >
            {state.running ? <Square size={13} /> : <Play size={14} />}{" "}
            {busy ? "Working…" : state.running ? "Stop server" : "Start server"}
          </button>
          <button
            className="button sidebar-test"
            disabled={!state.running || busy}
            onClick={() =>
              run(async () => {
                await api.SendTestMessage();
                setToast("Test email captured");
              })
            }
          >
            <Plus size={16} />
            Send test email
          </button>
        </section>
      </aside>
      <main>
        {error && (
          <div className="error" role="alert">
            <span>{error}</span>
            <button
              className="icon-button"
              aria-label="Dismiss error"
              onClick={() => setError("")}
            >
              <X size={16} />
            </button>
          </div>
        )}
        <section className="inbox-shell">
          <div className="inbox-toolbar">
            <div>
              <h2>
                {filter === "all"
                  ? "Inbox"
                  : filter === "unread"
                    ? "Unread"
                    : "Attachments"}
              </h2>
              <span className="count">{messages.length}</span>
              <span className="live-label">
                <i className={state.running ? "live" : ""} />
                {state.running ? "Live updates" : "Server offline"}
              </span>
            </div>
            <button
              className="text-button"
              disabled={!state.messages.length || busy}
              onClick={() => setModal("clear")}
            >
              <Trash2 size={14} />
              Clear inbox
            </button>
          </div>
          <div className="mail-workspace">
            <section className="message-pane" aria-label="Message list">
              <div className="search-wrap">
                <Search size={16} />
                <input
                  aria-label="Search messages"
                  placeholder="Search messages…"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
                {query && (
                  <button
                    className="icon-button"
                    aria-label="Clear search"
                    onClick={() => setQuery("")}
                  >
                    <X size={13} />
                  </button>
                )}
              </div>
              <div className="list-meta">
                <span>{query ? "SEARCH RESULTS" : "LATEST MESSAGES"}</span>
                <span>Newest first</span>
              </div>
              <div className="message-list">
                {messages.length === 0 ? (
                  <div className="list-empty">
                    <Inbox size={28} />
                    <strong>
                      {query
                        ? "No matches found"
                        : filter === "unread"
                          ? "All caught up"
                          : filter === "attachments"
                            ? "No attachments yet"
                            : "Your inbox is quiet"}
                    </strong>
                    <p>
                      {query
                        ? "Try a different subject or sender."
                        : "New messages will appear here."}
                    </p>
                  </div>
                ) : (
                  messages.map((m) => (
                    <button
                      key={m.id}
                      className={
                        "message-item " +
                        (selected?.id === m.id ? "selected " : "") +
                        (!m.read ? "unread" : "")
                      }
                      onClick={() => open(m.id)}
                    >
                      <div className="message-item-top">
                        <span className="sender">{sender(m.from)}</span>
                        <time>{time(m.receivedAt)}</time>
                      </div>
                      <div className="subject">
                        {!m.read && <i />}
                        {m.subject}
                      </div>
                      <p>{m.preview || "No text preview"}</p>
                      <div className="message-item-bottom">
                        <span>To: {m.to}</span>
                        {m.attachmentCount > 0 && (
                          <span>
                            <Paperclip size={12} />
                            {m.attachmentCount}
                          </span>
                        )}
                      </div>
                    </button>
                  ))
                )}
              </div>
              <div className="list-footer">
                <span>{state.unread} unread</span>
                <span>{state.messages.length} captured</span>
              </div>
            </section>
            <section className="detail-pane" aria-label="Message details">
              {!selected ? (
                <div className="detail-empty">
                  <div className="empty-illustration">
                    <span className="orbit one" />
                    <span className="orbit two" />
                    <div className="floating-mail">
                      <Mail size={45} strokeWidth={1.2} />
                      <span>
                        <Check size={13} />
                      </span>
                    </div>
                    <i className="spark s1" />
                    <i className="spark s2" />
                  </div>
                  <span className="eyebrow">GOOD THINGS ARE INCOMING</span>
                  <h2>
                    {state.messages.length
                      ? "Take a closer look."
                      : "Your next email starts here."}
                  </h2>
                  <p>
                    {state.messages.length
                      ? "Select a message to inspect its content, source, and attachments."
                      : "Point your app at the local SMTP server. Every email lands here, ready for a closer look."}
                  </p>
                  <div className="empty-address">
                    <Terminal size={15} />
                    <code>
                      {state.host}:{state.port}
                    </code>
                    <button
                      className="icon-button"
                      title="Copy address"
                      onClick={() => copy(`${state.host}:${state.port}`)}
                    >
                      <Copy size={14} />
                    </button>
                  </div>
                  <button
                    className="text-button accent"
                    onClick={() => setModal("help")}
                  >
                    View connection guide
                    <ArrowUpRight size={14} />
                  </button>
                </div>
              ) : (
                <>
                  <div className="detail-heading">
                    <div className="detail-tags">
                      <span>CAPTURED EMAIL</span>
                      <span>{size(selected.size)}</span>
                    </div>
                    <div className="detail-title">
                      <h2>{selected.subject}</h2>
                      <div className="detail-actions">
                        <button
                          className="icon-button"
                          title={selected.read ? "Mark unread" : "Mark read"}
                          onClick={toggleRead}
                          disabled={busy}
                        >
                          {selected.read ? (
                            <Mail size={17} />
                          ) : (
                            <MailOpen size={17} />
                          )}
                        </button>
                        <button
                          className="icon-button"
                          title="Export .eml"
                          onClick={save}
                          disabled={busy}
                        >
                          <ArrowDownToLine size={17} />
                        </button>
                        <button
                          className="icon-button danger"
                          title="Delete message"
                          disabled={busy}
                          onClick={() =>
                            run(() => api.DeleteMessage(selected.id))
                          }
                        >
                          <Trash2 size={17} />
                        </button>
                      </div>
                    </div>
                    <dl className="message-metadata">
                      <dt>From</dt>
                      <dd>{selected.from}</dd>
                      <dt>To</dt>
                      <dd>{selected.to}</dd>
                      <dt>Received</dt>
                      <dd>{new Date(selected.receivedAt).toLocaleString()}</dd>
                      <dt>Envelope</dt>
                      <dd>
                        {selected.envelopeFrom || "(bounce)"} →{" "}
                        {selected.recipients.join(", ")}
                      </dd>
                    </dl>
                  </div>
                  <div
                    className="tabbar"
                    role="tablist"
                    aria-label="Message format"
                  >
                    {(
                      ["preview", "text", "source", "attachments", "inspect"] as const
                    ).map((t) => (
                      <button
                        key={t}
                        role="tab"
                        aria-selected={tab === t}
                        className={tab === t ? "tab active" : "tab"}
                        onClick={() => setTab(t)}
                      >
                        {t === "preview" ? (
                          <MailOpen size={14} />
                        ) : t === "text" ? (
                          <FileText size={14} />
                        ) : t === "attachments" ? (
                          <Paperclip size={14} />
                        ) : (
                          <Code2 size={14} />
                        )}{" "}
                        {t === "preview"
                          ? "Preview"
                          : t === "text"
                            ? "Plain text"
                            : t === "attachments"
                              ? `Attachments (${selected.attachments.length})`
                              : t === "inspect" ? "Inspect" : "Raw source"}
                      </button>
                    ))}
                    <span>
                      {tab === "preview" && selected.html
                        ? "Remote content blocked"
                        : tab === "source"
                          ? "RFC 822"
                          : ""}
                    </span>
                  </div>
                  {tab === "preview" && selected.html && <div className="device-toolbar" aria-label="Preview width">
                    {(["desktop", "tablet", "mobile"] as const).map(d => {
                      const label = d === "desktop" ? "Full width" : d === "tablet" ? "Tablet · 768px" : "Mobile · 375px";
                      const Icon = d === "desktop" ? Monitor : d === "tablet" ? Tablet : Smartphone;
                      return <button key={d} className={device === d ? "device-control active" : "device-control"} aria-pressed={device === d} onClick={() => setDevice(d)}>
                        <span>{label}</span>
                        <Icon size={14} aria-hidden="true" />
                      </button>;
                    })}
                    <span>Viewport preview, not email-client emulation</span>
                  </div>}
                  <div className="message-content" role="tabpanel">
                    {tab === "inspect" && inspection ? (
                      <div className="inspection-view">
                        <h3>Content checks</h3>
                        <p>Local checks only; no spam score, delivery guarantee, or URL requests.</p>
                        {inspection.warnings.length ? <ul>{inspection.warnings.map(w => <li key={w}>{w}</li>)}</ul> : <p>No issues found by these basic checks.</p>}
                        <h3>Possible verification codes</h3>
                        <p>4–8 digit candidates can include dates and other numbers.</p>
                        <div className="code-candidates">{inspection.codes.map(code => <button className="button secondary" key={code} onClick={() => copy(code)}>{code}<Copy size={14}/></button>)}</div>
                        {!inspection.codes.length && <p>No candidates found.</p>}
                        <h3>Links ({inspection.links.length})</h3>
                        <p>Copy links to inspect them. Opening a verification link may consume its token.</p>
                        {inspection.links.map(link => <div className="inspection-row" key={link}><code>{link}</code><button className="icon-button" title="Copy link" onClick={() => copy(link)}><Copy size={14}/></button></div>)}
                        <h3>Headers</h3>
                        {inspection.headers.map((h, i) => <div className="inspection-row" key={i}><strong>{h.name}</strong><code>{h.value}</code></div>)}
                      </div>
                    ) : tab === "attachments" ? (
                      <div className="attachment-view">
                        <div className="attachment-heading">
                          <h3>Attachments</h3>
                          <span>
                            {selected.attachments.length} files ·{" "}
                            {size(
                              selected.attachments.reduce(
                                (total, file) => total + file.size,
                                0,
                              ),
                            )}
                          </span>
                        </div>
                        {selected.attachments.length === 0 ? (
                          <div className="list-empty">
                            <Paperclip size={30} />
                            <strong>No attachments</strong>
                            <p>This message has no attached files.</p>
                          </div>
                        ) : (
                          <div className="attachment-list">
                            {selected.attachments.map((a, i) => (
                              <div className="attachment-row" key={i}>
                                <div className="attachment-icon">
                                  <FileText size={22} />
                                </div>
                                <div className="attachment-info">
                                  <strong>{a.name}</strong>
                                  <span>
                                    {a.contentType || "Unknown file type"} ·{" "}
                                    {size(a.size)}
                                  </span>
                                </div>
                                <button
                                  className="button secondary"
                                  disabled={busy}
                                  onClick={() =>
                                    run(async () => {
                                      if (
                                        await api.SaveAttachment(selected.id, i)
                                      )
                                        setToast("Attachment saved");
                                    })
                                  }
                                >
                                  <ArrowDownToLine size={15} />
                                  Save
                                </button>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ) : tab === "preview" && selected.html ? (
                      <div className={"preview-frame " + device}><iframe
                        title="HTML email preview"
                        sandbox=""
                        referrerPolicy="no-referrer"
                        srcDoc={preview}
                      /></div>
                    ) : (
                      <pre className={tab === "source" ? "source" : ""}>
                        {tab === "source"
                          ? selected.raw
                          : selected.text ||
                            "This email has no plain-text part. Open Preview to view its HTML content."}
                      </pre>
                    )}
                  </div>
                </>
              )}
            </section>
          </div>
        </section>
      </main>
      {toast && (
        <div className="toast" role="status">
          <Check size={16} />
          {toast}
        </div>
      )}
      {modal && (
        <div className="modal-backdrop" onClick={() => setModal(null)}>
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-title"
            onClick={(e) => e.stopPropagation()}
            onKeyDown={(e) => {
              if (e.key === "Escape") setModal(null);
              if (e.key === "Tab") {
                const items = e.currentTarget.querySelectorAll<HTMLElement>(
                  "button:not(:disabled),input:not(:disabled)",
                );
                const first = items[0],
                  last = items[items.length - 1];
                if (e.shiftKey && document.activeElement === first) {
                  e.preventDefault();
                  last?.focus();
                } else if (!e.shiftKey && document.activeElement === last) {
                  e.preventDefault();
                  first?.focus();
                }
              }
            }}
          >
            <div className="modal-heading">
              <h2 id="modal-title">
                {modal === "settings"
                  ? "Server settings"
                  : modal === "help"
                    ? "Connect your application"
                    : "Clear your inbox?"}
              </h2>
              <button
                autoFocus
                className="icon-button"
                aria-label="Close dialog"
                onClick={() => setModal(null)}
              >
                <X size={20} />
              </button>
            </div>
            {modal === "settings" ? (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  setModal(null);
                  setToast("Settings saved. Start the server to apply.");
                }}
              >
                <p>
                  Choose where the SMTP server listens. Stop the server before
                  changing its address.
                </p>
                <label>
                  Host
                  <input
                    required
                    value={host}
                    disabled={state.running}
                    onChange={(e) => setHost(e.target.value)}
                  />
                </label>
                <label>
                  Port
                  <input
                    required
                    type="number"
                    min="1"
                    max="65535"
                    value={port}
                    disabled={state.running}
                    onChange={(e) => setPort(e.target.value)}
                  />
                </label>
                <div className="hint">
                  <ShieldCheck size={17} />
                  <span>
                    Use 127.0.0.1 to keep capture local. A public interface
                    exposes this unauthenticated inbox to your network.
                  </span>
                </div>
                <button className="button primary" type="submit">
                  Done
                </button>
              </form>
            ) : modal === "help" ? (
              <>
                <p>
                  Use these values in your app's email configuration. Messages
                  are captured locally and never sent to recipients.
                </p>
                <div className="config-grid">
                  <span>SMTP host</span>
                  <code>{state.host}</code>
                  <span>SMTP port</span>
                  <code>{state.port}</code>
                  <span>Authentication</span>
                  <code>None</code>
                  <span>TLS / SSL</span>
                  <code>Disabled</code>
                </div>
                <div className="code-heading">
                  <strong>Environment variables</strong>
                  <button
                    className="icon-button"
                    title="Copy configuration"
                    onClick={() =>
                      copy(
                        `SMTP_HOST=${state.host}\nSMTP_PORT=${state.port}\nSMTP_SECURE=false`,
                      )
                    }
                  >
                    <Copy size={15} />
                  </button>
                </div>
                <pre className="config-code">{`SMTP_HOST=${state.host}\nSMTP_PORT=${state.port}\nSMTP_SECURE=false`}</pre>
                <p className="hint">
                  Messages live in memory and are cleared when the app closes.
                  Export .eml files or save attachments to keep them.
                </p>
                <button
                  className="button primary"
                  disabled={!state.running || busy}
                  onClick={() => {
                    setModal(null);
                    run(() => api.SendTestMessage());
                  }}
                >
                  Send a test email
                  <ArrowUpRight size={15} />
                </button>
              </>
            ) : (
              <>
                <p>
                  This will permanently remove all {state.messages.length}{" "}
                  captured messages and their attachments from this session.
                </p>
                <div className="modal-actions">
                  <button
                    className="button secondary"
                    onClick={() => setModal(null)}
                  >
                    Cancel
                  </button>
                  <button
                    className="button destructive"
                    onClick={() => {
                      setModal(null);
                      run(() => api.ClearMessages());
                    }}
                  >
                    Clear all messages
                  </button>
                </div>
              </>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
