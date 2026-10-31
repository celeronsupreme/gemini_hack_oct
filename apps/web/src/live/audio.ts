// Microphone capture to 16 kHz PCM16 (base64 chunks) and 24 kHz PCM16 playback, using AudioWorklets built from
// inline source so there is nothing to serve separately. NEEDS TESTING ON A REAL DEVICE.

const CAPTURE_WORKLET = `
class PcmCapture extends AudioWorkletProcessor {
  constructor() { super(); this.buf = []; this.len = 0; this.target = 2048; }
  process(inputs) {
    const ch = inputs[0] && inputs[0][0];
    if (!ch) return true;
    const out = new Int16Array(ch.length);
    for (let i = 0; i < ch.length; i++) { const s = Math.max(-1, Math.min(1, ch[i])); out[i] = s < 0 ? s * 0x8000 : s * 0x7fff; }
    this.buf.push(out); this.len += out.length;
    if (this.len >= this.target) {
      const merged = new Int16Array(this.len); let o = 0;
      for (const b of this.buf) { merged.set(b, o); o += b.length; }
      this.port.postMessage(merged.buffer, [merged.buffer]); this.buf = []; this.len = 0;
    }
    return true;
  }
}
registerProcessor('pcm-capture', PcmCapture);`;

function b64(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf); let s = '';
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, Array.from(bytes.subarray(i, i + 0x8000)));
  return btoa(s);
}
function unb64(s: string): ArrayBuffer {
  const bin = atob(s); const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out.buffer;
}

export class MicCapture {
  private ctx: AudioContext | null = null;
  private stream: MediaStream | null = null;
  private node: AudioWorkletNode | null = null;
  constructor(private sampleRate: number, private onChunk: (base64: string) => void) {}
  async start() {
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
    this.ctx = new AudioContext({ sampleRate: this.sampleRate });
    const url = URL.createObjectURL(new Blob([CAPTURE_WORKLET], { type: 'application/javascript' }));
    await this.ctx.audioWorklet.addModule(url);
    const src = this.ctx.createMediaStreamSource(this.stream);
    this.node = new AudioWorkletNode(this.ctx, 'pcm-capture');
    this.node.port.onmessage = (e) => this.onChunk(b64(e.data as ArrayBuffer));
    src.connect(this.node); // not connected to destination: we do not want to hear ourselves
    if (this.ctx.state === 'suspended') await this.ctx.resume();
  }
  stop() {
    this.node?.disconnect(); this.stream?.getTracks().forEach((t) => t.stop()); void this.ctx?.close();
    this.node = null; this.stream = null; this.ctx = null;
  }
}

export class PcmPlayer {
  private ctx: AudioContext | null = null;
  private nextTime = 0;
  private sources: AudioBufferSourceNode[] = [];
  constructor(private sampleRate: number) {}
  async init() {
    this.ctx = new AudioContext({ sampleRate: this.sampleRate });
    if (this.ctx.state === 'suspended') await this.ctx.resume();
    this.nextTime = this.ctx.currentTime;
  }
  enqueue(base64: string) {
    if (!this.ctx) return;
    const pcm = new Int16Array(unb64(base64));
    const buf = this.ctx.createBuffer(1, pcm.length, this.sampleRate);
    const ch = buf.getChannelData(0);
    for (let i = 0; i < pcm.length; i++) ch[i] = pcm[i] / 0x8000;
    const src = this.ctx.createBufferSource(); src.buffer = buf; src.connect(this.ctx.destination);
    const start = Math.max(this.ctx.currentTime + 0.02, this.nextTime);
    src.start(start); this.nextTime = start + buf.duration;
    this.sources.push(src); src.onended = () => { this.sources = this.sources.filter((s) => s !== src); };
  }
  clear() { this.sources.forEach((s) => { try { s.stop(); } catch { /* already stopped */ } }); this.sources = []; if (this.ctx) this.nextTime = this.ctx.currentTime; }
  async close() { this.clear(); await this.ctx?.close(); this.ctx = null; }
}
