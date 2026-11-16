/**
 * Enregistrement au micro, converti en WAV mono 16 kHz : le format attendu par la reconnaissance vocale.
 *
 * Le navigateur enregistre en WebM/Opus (ou MP4 sur Safari) ; on décode puis on ré-échantillonne avec
 * l'API Web Audio, sans bibliothèque. Un WAV 16 kHz mono pèse 32 Ko par seconde (2 minutes ≈ 4 Mo).
 */

export const SAMPLE_RATE = 16_000

export function canRecord() {
  return typeof window !== 'undefined' && typeof MediaRecorder !== 'undefined' && Boolean(navigator.mediaDevices?.getUserMedia)
}

/** PCM 16 bits mono → fichier WAV. */
export function encodeWav(samples: Float32Array, sampleRate = SAMPLE_RATE): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2)
  const view = new DataView(buffer)
  const write = (offset: number, text: string) => [...text].forEach((c, i) => view.setUint8(offset + i, c.charCodeAt(0)))
  write(0, 'RIFF')
  view.setUint32(4, 36 + samples.length * 2, true)
  write(8, 'WAVE')
  write(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true) // PCM
  view.setUint16(22, 1, true) // mono
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  write(36, 'data')
  view.setUint32(40, samples.length * 2, true)
  samples.forEach((s, i) => {
    const v = Math.max(-1, Math.min(1, s))
    view.setInt16(44 + i * 2, v < 0 ? v * 0x8000 : v * 0x7fff, true)
  })
  return new Blob([buffer], { type: 'audio/wav' })
}

async function toWav(recorded: Blob): Promise<Blob> {
  const context = new AudioContext()
  try {
    const decoded = await context.decodeAudioData(await recorded.arrayBuffer())
    const length = Math.ceil(decoded.duration * SAMPLE_RATE)
    const offline = new OfflineAudioContext(1, Math.max(length, 1), SAMPLE_RATE)
    const source = offline.createBufferSource()
    source.buffer = decoded // plusieurs canaux : mélangés en mono par le contexte à 1 canal
    source.connect(offline.destination)
    source.start()
    const rendered = await offline.startRendering()
    return encodeWav(rendered.getChannelData(0))
  } finally {
    void context.close()
  }
}

export interface Recording {
  /** Arrête l'enregistrement et renvoie le WAV. */
  stop: () => Promise<Blob>
  /** Abandonne l'enregistrement (micro libéré). */
  cancel: () => void
}

export async function startRecording(): Promise<Recording> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } })
  const recorder = new MediaRecorder(stream)
  const chunks: Blob[] = []
  recorder.ondataavailable = (e) => e.data.size && chunks.push(e.data)
  const release = () => stream.getTracks().forEach((track) => track.stop())
  recorder.start()
  return {
    stop: () =>
      new Promise<Blob>((resolve, reject) => {
        recorder.onstop = () => {
          release()
          toWav(new Blob(chunks, { type: recorder.mimeType })).then(resolve, reject)
        }
        recorder.stop()
      }),
    cancel: () => {
      recorder.onstop = release
      if (recorder.state !== 'inactive') recorder.stop()
      else release()
    },
  }
}
