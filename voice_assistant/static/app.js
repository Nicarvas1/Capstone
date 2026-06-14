/* ── CONFIG ─────────────────────────────────────────────────────── */
const TARGET_SAMPLE_RATE = 16000;
const N_BARS             = 28;

/* ── DOM ─────────────────────────────────────────────────────────── */
const chat       = document.getElementById('chat');
const waveform   = document.getElementById('waveform');
const statusIcon = document.getElementById('status-icon');
const statusText = document.getElementById('status-text');
const connDot    = document.getElementById('conn-dot');
const connLabel  = document.getElementById('conn-label');
const ttsBtn     = document.getElementById('tts-btn');
const resetBtn   = document.getElementById('reset-btn');
const textInput  = document.getElementById('text-input');
const sendBtn    = document.getElementById('send-btn');
const micBtn     = document.getElementById('mic-btn');
const micLabel   = document.getElementById('mic-label');
const pills      = [1,2,3,4].map(i => document.getElementById(`pill-${i}`));

/* ── State ───────────────────────────────────────────────────────── */
let ws = null, audioCtx = null, analyser = null, processor = null;
let ttsEnabled    = false;
let isRecording   = false;
let recordChunks  = [];
let inputSampleRate = 44100;

/* ── Waveform bars ───────────────────────────────────────────────── */
const bars = [];
for (let i = 0; i < N_BARS; i++) {
  const b = document.createElement('div');
  b.className = 'wave-bar';
  waveform.appendChild(b);
  bars.push(b);
}

/* ── Helpers ─────────────────────────────────────────────────────── */
function setStatus(icon, text) { statusIcon.textContent = icon; statusText.textContent = text; }

function addMsg(role, text, extraClass = '') {
  const wrap = document.createElement('div');
  wrap.className = `msg ${role}${extraClass ? ' ' + extraClass : ''}`;
  const label = document.createElement('div');
  label.className = 'msg-label';
  label.textContent = role === 'user' ? 'Tú' : (extraClass === 'transcription' ? 'Transcripción' : 'Asistente PIE');
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;
  wrap.appendChild(label);
  wrap.appendChild(bubble);
  chat.appendChild(wrap);
  chat.scrollTop = chat.scrollHeight;
}

function addDownload(url, filename) {
  const wrap = document.createElement('div');
  wrap.className = 'msg ai';
  const a = document.createElement('a');
  a.className = 'download-btn';
  a.href = url; a.download = filename || 'Informe.docx';
  a.innerHTML = '📥 Descargar Informe Word';
  wrap.appendChild(a);
  chat.appendChild(wrap);
  chat.scrollTop = chat.scrollHeight;
}

function updatePills(etapa) {
  pills.forEach((p, i) => {
    p.classList.remove('active', 'done');
    if (i + 1 < etapa) p.classList.add('done');
    else if (i + 1 === etapa) p.classList.add('active');
  });
}

/* ── Editable form (full width) ──────────────────────────────────── */
function addForm(borrador) {
  // Render form as a standalone full-width element (not inside .msg bubble)
  const outer = document.createElement('div');
  outer.className = 'form-wrapper';

  const labelEl = document.createElement('div');
  labelEl.className = 'form-header-label';
  labelEl.textContent = '📋 Formulario editable — revisa y completa antes de generar';
  outer.appendChild(labelEl);

  const card = document.createElement('div');
  card.className = 'form-card';
  card.innerHTML = `
    <div class="form-grid">

      <div class="form-section">
        <div class="form-section-title">Evaluación</div>
        <div class="form-row two">
          <div class="field">
            <label>Motivo de evaluación</label>
            <select name="motivo_evaluacion">
              <option value="Ingreso" ${borrador.motivo_evaluacion === 'Ingreso' ? 'selected' : ''}>Ingreso</option>
              <option value="Reevaluación" ${borrador.motivo_evaluacion === 'Reevaluación' ? 'selected' : ''}>Reevaluación</option>
            </select>
          </div>
          <div class="field">
            <label>Fecha de evaluación</label>
            <input name="fecha_evaluacion" type="text" value="${borrador.fecha_evaluacion || ''}">
          </div>
        </div>
        <div class="field">
          <label>Instrumentos aplicados</label>
          <textarea name="instrumentos_aplicados">${borrador.instrumentos_aplicados || ''}</textarea>
        </div>
        <div class="field">
          <label>Diagnóstico NEE</label>
          <textarea name="diagnostico_nee">${borrador.diagnostico_nee || ''}</textarea>
        </div>
      </div>

      <div class="form-section">
        <div class="form-section-title">Área Pedagógica</div>
        <div class="field">
          <label>Fortalezas pedagógicas</label>
          <textarea name="fortalezas_pedagogicas">${borrador.fortalezas_pedagogicas || ''}</textarea>
        </div>
        <div class="field">
          <label>Necesidades pedagógicas</label>
          <textarea name="necesidades_pedagogicas">${borrador.necesidades_pedagogicas || ''}</textarea>
        </div>
      </div>

      <div class="form-section">
        <div class="form-section-title">Área Social</div>
        <div class="field">
          <label>Fortalezas sociales</label>
          <textarea name="fortalezas_sociales">${borrador.fortalezas_sociales || ''}</textarea>
        </div>
        <div class="field">
          <label>Necesidades sociales</label>
          <textarea name="necesidades_sociales">${borrador.necesidades_sociales || ''}</textarea>
        </div>
      </div>

      <div class="form-section">
        <div class="form-section-title">Acuerdos y Compromisos</div>
        <div class="field">
          <label>Trabajo colaborativo</label>
          <textarea name="trabajo_colaborativo">${borrador.trabajo_colaborativo || ''}</textarea>
        </div>
        <div class="field">
          <label>Apoyos en el hogar</label>
          <textarea name="apoyos_hogar">${borrador.apoyos_hogar || ''}</textarea>
        </div>
        <div class="field">
          <label>Acuerdos y compromisos</label>
          <textarea name="acuerdos_compromisos">${borrador.acuerdos_compromisos || ''}</textarea>
        </div>
        <div class="form-row two">
          <div class="field">
            <label>Próximas fechas de evaluación</label>
            <input name="fechas_evaluacion" type="text" value="${borrador.fechas_evaluacion || ''}">
          </div>
        </div>
      </div>

      <div class="form-section">
        <div class="form-section-title">Apoderado / Receptor</div>
        <div class="form-row two">
          <div class="field">
            <label>Tipo de apoderado</label>
            <select name="tipo_apoderado">
              <option value="Apoderado/a titular" ${borrador.tipo_apoderado === 'Apoderado/a titular' ? 'selected' : ''}>Apoderado/a titular</option>
              <option value="Apoderado/a suplente" ${borrador.tipo_apoderado === 'Apoderado/a suplente' ? 'selected' : ''}>Apoderado/a suplente</option>
            </select>
          </div>
          <div class="field">
            <label>Poder simple</label>
            <select name="poder_simple">
              <option value="No Aplica" ${(!borrador.poder_simple || borrador.poder_simple === 'No Aplica') ? 'selected' : ''}>No Aplica</option>
              <option value="Sí" ${borrador.poder_simple === 'Sí' ? 'selected' : ''}>Sí</option>
              <option value="No" ${borrador.poder_simple === 'No' ? 'selected' : ''}>No</option>
            </select>
          </div>
        </div>
      </div>

    </div>

    <div class="form-actions">
      <button class="btn-gen" id="gen-word-btn">📄 Generar Word</button>
    </div>
  `;

  // Hidden fields from borrador (receptor data)
  ['nombre_receptor','rut_receptor','nombre_social_receptor',
   'telefono_receptor','email_receptor','relacion_receptor','presencia_receptor'].forEach(k => {
    const inp = document.createElement('input');
    inp.type = 'hidden'; inp.name = k; inp.value = borrador[k] || '';
    card.appendChild(inp);
  });

  // Submit handler
  card.querySelector('#gen-word-btn').addEventListener('click', () => {
    const btn = card.querySelector('#gen-word-btn');
    btn.disabled = true; btn.textContent = '⏳ Generando...';
    const datos = {};
    card.querySelectorAll('[name]').forEach(el => { if (el.name) datos[el.name] = el.value; });
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'generar_word', datos }));
    }
  });

  outer.appendChild(card);
  chat.appendChild(outer);
  chat.scrollTop = chat.scrollHeight;
}

/* ── WAV encoder ─────────────────────────────────────────────────── */
function writeStr(view, off, str) {
  for (let i = 0; i < str.length; i++) view.setUint8(off + i, str.charCodeAt(i));
}
function encodeWAV(chunks, sr) {
  let total = chunks.reduce((s,c) => s + c.length, 0);
  const pcm = new Float32Array(total);
  let off = 0; for (const c of chunks) { pcm.set(c, off); off += c.length; }
  const buf = new ArrayBuffer(44 + pcm.length * 2);
  const v = new DataView(buf);
  writeStr(v,0,'RIFF'); v.setUint32(4,36+pcm.length*2,true); writeStr(v,8,'WAVE');
  writeStr(v,12,'fmt '); v.setUint32(16,16,true); v.setUint16(20,1,true); v.setUint16(22,1,true);
  v.setUint32(24,sr,true); v.setUint32(28,sr*2,true); v.setUint16(32,2,true); v.setUint16(34,16,true);
  writeStr(v,36,'data'); v.setUint32(40,pcm.length*2,true);
  let bo = 44;
  for (let i = 0; i < pcm.length; i++) {
    const s = Math.max(-1, Math.min(1, pcm[i]));
    v.setInt16(bo, s<0 ? s*0x8000 : s*0x7FFF, true); bo += 2;
  }
  return buf;
}

function resample(data, srcSR, dstSR) {
  if (srcSR === dstSR) return data;
  const ratio = dstSR / srcSR;
  const out = new Float32Array(Math.round(data.length * ratio));
  for (let i = 0; i < out.length; i++) {
    const si = i/ratio, lo = Math.floor(si), hi = Math.min(lo+1, data.length-1), t = si-lo;
    out[i] = data[lo]*(1-t) + data[hi]*t;
  }
  return out;
}

/* ── WebSocket ───────────────────────────────────────────────────── */
function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  ws = new WebSocket(`${proto}://${location.host}/ws`);

  ws.onopen = () => { connDot.classList.add('connected'); connLabel.textContent = 'Conectado'; };
  ws.onclose = () => {
    connDot.classList.remove('connected'); connLabel.textContent = 'Desconectado';
    setTimeout(connectWS, 2000);
  };
  ws.onerror = () => setStatus('❌', 'Error de conexión.');

  ws.onmessage = async (e) => {
    const msg = JSON.parse(e.data);

    if (msg.type === 'status') {
      setStatus('⏳', msg.text);

    } else if (msg.type === 'transcription') {
      addMsg('user', msg.text, 'transcription');
      setStatus('⏳', 'Procesando...');

    } else if (msg.type === 'user_echo') {
      addMsg('user', msg.text);
      setStatus('⏳', 'Procesando...');

    } else if (msg.type === 'response') {
      addMsg('ai', msg.text);
      if (msg.etapa) updatePills(msg.etapa);
      if (msg.accion === 'mostrar_formulario' && msg.borrador) addForm(msg.borrador);
      if (msg.accion === 'documento_listo' && msg.download_url) {
        addDownload(msg.download_url, msg.download_url.split('/').pop());
      }
      setStatus('🎤', 'Presiona el micrófono para hablar');

    } else if (msg.type === 'tts_audio' && msg.audio) {
      const bytes = Uint8Array.from(atob(msg.audio), c => c.charCodeAt(0));
      const url = URL.createObjectURL(new Blob([bytes], { type: 'audio/wav' }));
      const audio = new Audio(url);
      audio.onended = () => URL.revokeObjectURL(url);
      audio.play().catch(()=>{});

    } else if (msg.type === 'error') {
      addMsg('ai', '⚠️ ' + msg.text);
      setStatus('🎤', 'Presiona el micrófono para hablar');
    }
  };
}

/* ── Mic init (audio context, no auto-listen) ────────────────────── */
async function initMic() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    audioCtx = new AudioContext();
    inputSampleRate = audioCtx.sampleRate;
    const source = audioCtx.createMediaStreamSource(stream);

    analyser = audioCtx.createAnalyser();
    analyser.fftSize = 256;
    source.connect(analyser);

    // Processor only collects when isRecording = true
    processor = audioCtx.createScriptProcessor(2048, 1, 1);
    source.connect(processor);
    processor.connect(audioCtx.destination);

    processor.onaudioprocess = (ev) => {
      if (!isRecording) return;
      const raw = ev.inputBuffer.getChannelData(0);
      recordChunks.push(resample(new Float32Array(raw), inputSampleRate, TARGET_SAMPLE_RATE));
    };

    setStatus('🎤', 'Presiona el micrófono para hablar');
    micBtn.disabled = false;
    requestAnimationFrame(drawWave);

  } catch (err) {
    setStatus('❌', 'Sin acceso al micrófono: ' + err.message);
    micBtn.disabled = true;
  }
}

/* ── Push-to-Talk button ─────────────────────────────────────────── */
function startRecording() {
  if (isRecording || !audioCtx) return;
  isRecording  = true;
  recordChunks = [];
  micBtn.classList.add('recording');
  micLabel.textContent = 'Suelta para enviar';
  setStatus('🔴', 'Grabando...');
}

function stopRecording() {
  if (!isRecording) return;
  isRecording = false;
  micBtn.classList.remove('recording');
  micLabel.textContent = 'Mantén para hablar';
  if (recordChunks.length > 0 && ws && ws.readyState === WebSocket.OPEN) {
    ws.send(encodeWAV(recordChunks, TARGET_SAMPLE_RATE));
    setStatus('⏳', 'Enviando...');
  } else {
    setStatus('🎤', 'Presiona el micrófono para hablar');
  }
  recordChunks = [];
}

micBtn.addEventListener('mousedown',  (e) => { e.preventDefault(); startRecording(); });
micBtn.addEventListener('mouseup',    stopRecording);
micBtn.addEventListener('mouseleave', stopRecording);
micBtn.addEventListener('touchstart', (e) => { e.preventDefault(); startRecording(); }, { passive: false });
micBtn.addEventListener('touchend',   (e) => { e.preventDefault(); stopRecording(); },  { passive: false });

/* ── Waveform ────────────────────────────────────────────────────── */
const freqBuf = new Uint8Array(128);
function drawWave() {
  requestAnimationFrame(drawWave);
  if (!analyser) return;
  analyser.getByteFrequencyData(freqBuf);
  const step = Math.floor(freqBuf.length / N_BARS);
  for (let i = 0; i < N_BARS; i++) {
    const h = Math.max(3, (freqBuf[i*step]/255) * 32);
    bars[i].style.height = h + 'px';
    bars[i].classList.toggle('recording', isRecording);
  }
}

/* ── Text input (textarea auto-grow) ────────────────────────────── */
function autoResize() {
  textInput.style.height = 'auto';
  textInput.style.height = Math.min(textInput.scrollHeight, 180) + 'px';
}

function sendText() {
  const text = textInput.value.trim();
  if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
  ws.send(JSON.stringify({ type: 'text_message', text }));
  textInput.value = '';
  // Reset height after clearing
  textInput.style.height = 'auto';
}

textInput.addEventListener('input', autoResize);
sendBtn.addEventListener('click', sendText);
textInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendText(); }
});

/* ── TTS toggle ──────────────────────────────────────────────────── */
ttsBtn.addEventListener('click', () => {
  ttsEnabled = !ttsEnabled;
  ttsBtn.classList.toggle('on', ttsEnabled);
  ttsBtn.textContent = ttsEnabled ? '🔊 Voz IA' : '🔇 Voz IA';
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'tts_toggle', enabled: ttsEnabled }));
  }
});

/* ── Reset ───────────────────────────────────────────────────────── */
resetBtn.addEventListener('click', () => {
  if (confirm('¿Iniciar un nuevo informe? Se perderá la conversación actual.')) {
    chat.innerHTML = '';
    updatePills(1);
    ttsEnabled = false; ttsBtn.classList.remove('on'); ttsBtn.textContent = '🔇 Voz IA';
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'reset' }));
  }
});

/* ── Boot ────────────────────────────────────────────────────────── */
connectWS();
initMic();
