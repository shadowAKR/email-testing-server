export interface Attachment {
  name: string;
  contentType: string;
  contentId?: string;
  size: number;
  /** Base64-encoded bytes supplied only for CID-backed inline images. */
  inlineData?: string;
}
export interface Summary {
  id: string;
  from: string;
  to: string;
  subject: string;
  preview: string;
  receivedAt: string;
  read: boolean;
  size: number;
  attachmentCount: number;
}
export interface Message extends Omit<Summary, "preview" | "attachmentCount"> {
  text: string;
  html: string;
  raw: string;
  date: string;
  envelopeFrom: string;
  recipients: string[];
  attachments: Attachment[];
}
export interface State {
  running: boolean;
  host: string;
  port: number;
  received: number;
  unread: number;
  messages: Summary[];
}
export interface Inspection {
  headers: { name: string; value: string }[];
  links: string[];
  codes: string[];
  warnings: string[];
}
interface API {
  InspectMessage(id: string): Promise<Inspection>;
  ImportMessage(): Promise<boolean>;
  ExportInbox(): Promise<boolean>;
  OpenContribute(): Promise<void>;
  GetState(): Promise<State>;
  StartServer(host: string, port: number): Promise<void>;
  StopServer(): Promise<void>;
  GetMessage(id: string): Promise<Message>;
  SetRead(id: string, read: boolean): Promise<void>;
  DeleteMessage(id: string): Promise<void>;
  ClearMessages(): Promise<void>;
  SaveAttachment(id: string, index: number): Promise<boolean>;
  ExportMessage(id: string): Promise<boolean>;
  SendTestMessage(): Promise<void>;
}
declare global {
  interface Window {
    go?: { main: { App: API } };
    runtime?: { EventsOn: (name: string, callback: () => void) => () => void };
  }
}
export const api = new Proxy({} as API, {
  get:
    (_, key) =>
    (...args: unknown[]) => {
      const backend = window.go?.main.App;
      if (!backend)
        return Promise.reject(
          new Error(
            "Open the desktop app with wails dev to connect to the Go backend.",
          ),
        );
      return (
        backend[key as keyof API] as (...args: unknown[]) => Promise<unknown>
      )(...args);
    },
});
