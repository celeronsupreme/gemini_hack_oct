// Gemini Live API client for the browser. Connects with an ephemeral token minted by our backend (never the API key),
// streams 16 kHz PCM from the microphone, plays 24 kHz PCM back, surfaces both transcriptions, and forwards tool calls
// to POST /live/tool so the backend validates and stores them.
//
// Protocol (BidiGenerateContent over WebSocket), per Google's Live API docs as of Oct 2026:
//   client -> { setup: {...} }                      first message
//   server -> { setupComplete: {} }
//   client -> { realtimeInput: { audio: { data: base64 PCM16 16k, mimeType: "audio/pcm;rate=16000" } } }
//   server -> { serverContent: { modelTurn: { parts: [{ inlineData: { data, mimeType } }] }, inputTranscription?: {text},
//                                outputTranscription?: {text}, interrupted?: true, turnComplete?: true, generationComplete?: true } }
//   server -> { toolCall: { functionCalls: [{ id, name, args }] } }     client -> { toolResponse: { functionResponses: [...] } }
//   server -> { toolCallCancellation: { ids } } | { goAway: { timeLeft } } | { sessionResumptionUpdate: { newHandle, resumable } }
// NEEDS TESTING ON A REAL DEVICE: mic permissions, worklet loading over https, iOS Safari AudioContext unlock.
import type { LiveToken } from '@seizure/contracts';
import { api } from '@/api/client';
import { MicCapture, PcmPlayer } from './audio';

export type LiveEvent =
  | { type: 'status'; text: string }
  | { type: 'user_text'; text: string }
  | { type: 'model_text'; text: string }
  | { type: 'tool'; name: string; args: Record<string, unknown>; response: Record<string, unknown> }
  | { type: 'turn_complete' }
  | { type: 'error'; text: string };

const ENDPOINT = 'wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContentConstrained';

export class LiveSession {
  private ws: WebSocket | null = null;
  private mic: MicCapture | null = null;
  private player = new PcmPlayer(24000);
  private resumeHandle: string | null = null;
  private token: LiveToken | null = null;
  transcript: { role: 'user' | 'model'; text: string }[] = [];
  onEvent: (e: LiveEvent) => void = () => {};

  async start(): Promise<void> {
    this.token = await api.liveToken();
    if (this.token.mock) {
      this.onEvent({ type: 'status', text: 'Gemini is not configured on the server (mock token). Type or paste what happened instead.' });
      return;
    }
    await this.player.init();
    this.ws = new WebSocket(`${ENDPOINT}?access_token=${encodeURIComponent(this.token.token)}`);
    this.ws.onopen = () => this.sendSetup(true);
    this.ws.onmessage = (m) => void this.handle(m);
    this.ws.onerror = () => this.onEvent({ type: 'error', text: 'WebSocket error' });
    this.ws.onclose = (e) => this.onEvent({ type: 'status', text: `Session closed (${e.code})` });
  }

  private sendSetup(withVocabulary: boolean) {
    if (!this.ws || !this.token) return;
    const setup: Record<string, unknown> = {
      model: `models/${this.token.model}`,
      generationConfig: { responseModalities: ['AUDIO'] },
      systemInstruction: { parts: [{ text: this.token.system_instruction }] },
      tools: [{ functionDeclarations: this.token.tool_declarations }],
      inputAudioTranscription: withVocabulary ? { customVocabulary: this.token.custom_vocabulary } : {},
      outputAudioTranscription: {},
      realtimeInputConfig: { automaticActivityDetection: { silenceDurationMs: 700 } },
      contextWindowCompression: { slidingWindow: {} },
      sessionResumption: this.resumeHandle ? { handle: this.resumeHandle } : {},
    };
    this.ws.send(JSON.stringify({ setup }));
    this.vocabularyTried = withVocabulary;
  }
  private vocabularyTried = false;

  private async handle(m: MessageEvent) {
    const text = typeof m.data === 'string' ? m.data : await (m.data as Blob).text();
    let msg: Record<string, unknown>;
    try { msg = JSON.parse(text); } catch { return; }
    if (msg.setupComplete !== undefined) {
      this.onEvent({ type: 'status', text: 'Listening' });
      await this.startMic();
      return;
    }
    if (msg.error) {
      const err = msg.error as { message?: string };
      if (this.vocabularyTried && /vocabulary/i.test(err.message || '')) { this.sendSetup(false); return; }
      this.onEvent({ type: 'error', text: err.message || 'error' });
      return;
    }
    const sc = msg.serverContent as Record<string, unknown> | undefined;
    if (sc) {
      if (sc.interrupted) this.player.clear();
      const turn = sc.modelTurn as { parts?: { inlineData?: { data: string; mimeType: string } }[] } | undefined;
      turn?.parts?.forEach((p) => { if (p.inlineData?.data) this.player.enqueue(p.inlineData.data); });
      const it = sc.inputTranscription as { text?: string } | undefined;
      if (it?.text) { this.pushTranscript('user', it.text); this.onEvent({ type: 'user_text', text: it.text }); }
      const ot = sc.outputTranscription as { text?: string } | undefined;
      if (ot?.text) { this.pushTranscript('model', ot.text); this.onEvent({ type: 'model_text', text: ot.text }); }
      if (sc.turnComplete) this.onEvent({ type: 'turn_complete' });
    }
    const tc = msg.toolCall as { functionCalls?: { id: string; name: string; args: Record<string, unknown> }[] } | undefined;
    if (tc?.functionCalls?.length) {
      const responses = [];
      for (const call of tc.functionCalls) {
        const res = await api.liveTool({ id: call.id, name: call.name, args: call.args || {} });
        this.onEvent({ type: 'tool', name: call.name, args: call.args || {}, response: res.response });
        responses.push({ id: call.id, name: call.name, response: res.response, scheduling: 'WHEN_IDLE' });
      }
      this.ws?.send(JSON.stringify({ toolResponse: { functionResponses: responses } }));
    }
    const sru = msg.sessionResumptionUpdate as { newHandle?: string; resumable?: boolean } | undefined;
    if (sru?.resumable && sru.newHandle) this.resumeHandle = sru.newHandle;
    if (msg.goAway) this.onEvent({ type: 'status', text: 'Session ending soon; will reconnect' });
  }

  private pushTranscript(role: 'user' | 'model', text: string) {
    const last = this.transcript[this.transcript.length - 1];
    if (last && last.role === role) last.text += text; else this.transcript.push({ role, text });
  }

  private async startMic() {
    this.mic = new MicCapture(16000, (base64) => {
      if (this.ws?.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify({ realtimeInput: { audio: { data: base64, mimeType: 'audio/pcm;rate=16000' } } }));
    });
    await this.mic.start();
  }

  sendText(text: string) {
    this.pushTranscript('user', text);
    this.ws?.send(JSON.stringify({ clientContent: { turns: [{ role: 'user', parts: [{ text }] }], turnComplete: true } }));
  }

  transcriptText(): string {
    return this.transcript.map((t) => `${t.role === 'user' ? 'Carer' : 'Assistant'}: ${t.text.trim()}`).join('\n');
  }

  async stop() {
    this.mic?.stop(); this.mic = null;
    if (this.ws?.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify({ realtimeInput: { audioStreamEnd: true } }));
    this.ws?.close(); this.ws = null;
    await this.player.close();
  }
}
