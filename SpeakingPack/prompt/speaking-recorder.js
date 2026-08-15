(() => {
  "use strict";

  const DB_NAME = "kooshky-speaking-recordings";
  const STORE = "takes";
  const DB_VERSION = 1;
  const LIMIT_MS = 45000;
  const WARNING_BYTES = 50 * 1024 * 1024;
  const topic = document.querySelector("#page-title")?.textContent.trim() || "Speaking Pack";
  const library = document.querySelector("#recording-library");
  if (!library) return;

  const message = document.querySelector("#recording-message");
  const transcribeOption = document.querySelector("#transcribe-new");
  const microphoneSelect = document.querySelector("#microphone-select");
  let dbPromise;
  let active = null;
  let playbackUrls = [];

  const say = (text, error = false) => {
    message.textContent = text;
    message.style.color = error ? "#a52b20" : "";
  };
  const safeName = value => value.normalize("NFKD").replace(/[^\w\s-]/g, "").trim().replace(/\s+/g, "-").replace(/-+/g, "-").slice(0, 80) || "recording";
  const stamp = value => new Date(value).toISOString().replace(/[:.]/g, "-");
  const humanBytes = bytes => bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : bytes < 1024 ** 3 ? `${(bytes / 1024 ** 2).toFixed(1)} MB` : `${(bytes / 1024 ** 3).toFixed(2)} GB`;
  const extensionFor = mime => mime.includes("wav") ? "wav" : mime.includes("ogg") ? "ogg" : mime.includes("mp4") ? "m4a" : "webm";
  const download = (blob, filename) => {
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(link.href), 30000);
  };

  function openDb() {
    if (!dbPromise) dbPromise = new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);
      request.onupgradeneeded = () => {
        const store = request.result.createObjectStore(STORE, { keyPath: "id" });
        store.createIndex("topic", "topic");
        store.createIndex("questionKey", "questionKey");
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
    return dbPromise;
  }

  async function transaction(mode, operation) {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, mode);
      const store = tx.objectStore(STORE);
      let result;
      try { result = operation(store); } catch (error) { reject(error); return; }
      tx.oncomplete = () => resolve(result);
      tx.onerror = () => reject(tx.error);
      tx.onabort = () => reject(tx.error || new Error("Storage operation was aborted."));
    });
  }

  const getAll = () => new Promise(async (resolve, reject) => {
    try {
      const db = await openDb();
      const request = db.transaction(STORE).objectStore(STORE).getAll();
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    } catch (error) { reject(error); }
  });
  const put = take => transaction("readwrite", store => store.put(take));
  const remove = id => transaction("readwrite", store => store.delete(id));
  const clear = () => transaction("readwrite", store => store.clear());

  async function refreshMicrophones() {
    if (!navigator.mediaDevices?.enumerateDevices) return;
    const selected = microphoneSelect.value;
    const devices = (await navigator.mediaDevices.enumerateDevices()).filter(device => device.kind === "audioinput");
    const options = [new Option("System default microphone", "")];
    devices.filter(device => device.deviceId !== "default").forEach((device, index) => {
      options.push(new Option(device.label || `Microphone ${index + 1}`, device.deviceId));
    });
    microphoneSelect.replaceChildren(...options);
    if ([...microphoneSelect.options].some(option => option.value === selected)) microphoneSelect.value = selected;
  }

  function questionDetails(card, setIndex, questionIndex) {
    const set = card.closest(".interview-set");
    const setTitle = set.querySelector("h3")?.textContent.trim() || `Interview Set ${setIndex + 1}`;
    const wording = card.querySelector(":scope > p")?.textContent.replace(/^Q\d+\.\s*/, "").trim() || `Question ${questionIndex + 1}`;
    return {
      setTitle,
      wording,
      questionNumber: questionIndex + 1,
      questionKey: `${topic}\u241f${setTitle}\u241f${questionIndex + 1}`
    };
  }

  async function beep() {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;
    const context = new AudioContext();
    await context.resume();
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.frequency.value = 880;
    gain.gain.setValueAtTime(.0001, context.currentTime);
    gain.gain.exponentialRampToValueAtTime(.18, context.currentTime + .02);
    gain.gain.exponentialRampToValueAtTime(.0001, context.currentTime + .28);
    oscillator.connect(gain).connect(context.destination);
    oscillator.start();
    oscillator.stop(context.currentTime + .3);
    await new Promise(resolve => setTimeout(resolve, 420));
    context.close();
  }

  function recognitionSession() {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!transcribeOption.checked) return null;
    if (!Recognition) {
      say("Live transcription is unavailable in this browser. The audio will still be recorded.", true);
      return null;
    }
    const recognition = new Recognition();
    recognition.lang = "en-US";
    recognition.continuous = true;
    recognition.interimResults = true;
    let finalText = "", interimText = "";
    recognition.onresult = event => {
      interimText = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const text = event.results[i][0].transcript.trim();
        if (event.results[i].isFinal) finalText += `${text} `;
        else interimText += `${text} `;
      }
      active.transcript = `${finalText}${interimText}`.trim();
    };
    recognition.onerror = event => {
      if (!['aborted', 'no-speech'].includes(event.error)) say(`Transcription stopped: ${event.error}. Your audio is still being recorded.`, true);
    };
    return recognition;
  }

  async function startRecording(button, details, panel) {
    if (active) { say("Finish the current recording before starting another.", true); return; }
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder || !AudioContext || !window.indexedDB) {
      say("Audio recording is not supported in this browser. Try a current version of Chrome, Edge, Firefox, or Safari.", true);
      return;
    }
    try {
      const estimate = await navigator.storage?.estimate?.();
      if (estimate?.quota && estimate.quota - estimate.usage < WARNING_BYTES) {
        say("Less than 50 MB of browser storage appears available. Download a backup and remove old takes before recording more.", true);
      }
      const deviceId = microphoneSelect.value;
      const stream = await navigator.mediaDevices.getUserMedia({ audio: deviceId ? { deviceId: { exact: deviceId } } : true });
      await refreshMicrophones();
      const track = stream.getAudioTracks()[0];
      if (!track || track.readyState !== "live") throw new Error("The browser did not provide a live microphone track.");
      track.enabled = true;
      const recognition = recognitionSession();
      const recorder = new MediaRecorder(stream);
      const chunks = [];
      const context = new AudioContext();
      await context.resume();
      const source = context.createMediaStreamSource(stream);
      const analyser = context.createAnalyser();
      analyser.fftSize = 1024;
      const silentOutput = context.createGain();
      silentOutput.gain.value = 0;
      source.connect(analyser);
      analyser.connect(silentOutput);
      silentOutput.connect(context.destination);
      const monitor = { context, source, analyser, silentOutput, samples: new Float32Array(analyser.fftSize), peak: 0 };
      active = { recorder, chunks, stream, recognition, transcript: "", started: 0, timer: null, timeout: null, button, details, panel, monitor, finishing: false };
      button.disabled = true;
      button.textContent = "Get ready…";
      await beep();
      recorder.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
      recorder.onstop = () => finishRecording();
      recorder.onerror = event => say(`The browser recorder reported an error: ${event.error?.message || event.error?.name || "unknown recording error"}.`, true);
      track.onmute = () => say(`Chrome muted the selected input (${track.label || "default microphone"}). Check Chrome’s microphone selector and your system input settings.`, true);
      track.onended = () => { if (active) say("The microphone input ended before the recording finished.", true); };
      recorder.start();
      active.started = Date.now();
      try { recognition?.start(); } catch (_) {}
      button.disabled = false;
      button.classList.add("is-recording");
      button.textContent = "Stop and save";
      const countdown = panel.querySelector(".recording-countdown");
      const tick = () => {
        countdown.textContent = `${Math.max(0, 45 - Math.floor((Date.now() - active.started) / 1000))} seconds left`;
        active.monitor.analyser.getFloatTimeDomainData(active.monitor.samples);
        for (const sample of active.monitor.samples) active.monitor.peak = Math.max(active.monitor.peak, Math.abs(sample));
      };
      tick();
      active.timer = setInterval(tick, 250);
      active.timeout = setTimeout(stopRecording, LIMIT_MS);
      const inputName = track.label ? ` using ${track.label}` : "";
      say(transcribeOption.checked && recognition ? `Recording${inputName} with live transcription.` : `Recording${inputName}. It will stop automatically at 45 seconds.`);
    } catch (error) {
      active?.stream?.getTracks().forEach(track => track.stop());
      active = null;
      button.disabled = false;
      button.textContent = "Record a 45-second answer";
      say(error.name === "NotAllowedError" ? "Microphone permission was denied. Allow microphone access in your browser settings and try again." : `Could not start recording: ${error.message}`, true);
    }
  }

  function stopRecording() {
    if (!active || active.finishing) return;
    active.finishing = true;
    clearTimeout(active.timeout);
    clearInterval(active.timer);
    active.button.disabled = true;
    active.button.textContent = "Saving…";
    active.panel.querySelector(".recording-countdown").textContent = "";
    try { active.recognition?.stop(); } catch (_) {}
    if (active.recorder.state !== "inactive") active.recorder.stop();
  }

  async function finishRecording() {
    const session = active;
    if (!session) return;
    session.stream.getTracks().forEach(track => track.stop());
    session.monitor.source.disconnect();
    session.monitor.analyser.disconnect();
    session.monitor.silentOutput.disconnect();
    await session.monitor.context.close().catch(() => {});
    const duration = Math.min(LIMIT_MS, Date.now() - session.started);
    const blob = new Blob(session.chunks, { type: session.recorder.mimeType || "audio/webm" });
    if (!blob.size) {
      session.button.disabled = false;
      session.button.classList.remove("is-recording");
      session.button.textContent = "Try recording again";
      active = null;
      say("The browser returned an empty audio file, so it was not saved. Check microphone permission and the selected input device, then try again.", true);
      return;
    }
    const take = {
      id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`,
      version: 1, topic, ...session.details, createdAt: new Date().toISOString(), duration, mimeType: blob.type,
      transcript: session.transcript.trim(), audio: blob
    };
    try {
      await put(take);
      if (session.monitor.peak < .001) {
        say("Saved the take, but the microphone signal appeared silent. Check the selected microphone and its system input level before trying again.", true);
      } else {
        say(`Saved a ${Math.round(duration / 1000)}-second take locally${take.transcript ? " with its transcript" : ""}. Remember to download backups regularly.`);
      }
    } catch (error) {
      if (error?.name === "QuotaExceededError") {
        say("Browser storage is full. This new take could not be saved. Download a backup, clear older data, and try again.", true);
        download(blob, `${safeName(topic)}--unsaved-${stamp(take.createdAt)}.${extensionFor(blob.type)}`);
      } else say(`The take could not be saved: ${error.message}`, true);
    }
    session.button.disabled = false;
    session.button.classList.remove("is-recording");
    session.button.textContent = "Record another take";
    active = null;
    await refresh();
  }

  function renderTake(take) {
    const article = document.createElement("article");
    article.className = "take";
    const url = URL.createObjectURL(take.audio);
    playbackUrls.push(url);
    const date = new Date(take.createdAt);
    article.innerHTML = `<div class="take-head"><strong>Take from ${date.toLocaleString()}</strong><span class="take-note">${Math.round(take.duration / 1000)} sec · ${humanBytes(take.audio.size)}</span></div><audio controls preload="metadata" src="${url}"></audio><label><span class="take-note">Transcript (editable and saved automatically)</span><textarea placeholder="No transcript was captured. You can type or paste one here."></textarea></label><div class="take-actions"><button data-audio type="button">Download audio</button><button data-text type="button">Download transcript</button><button class="danger" data-delete type="button">Delete take</button></div>`;
    const textarea = article.querySelector("textarea");
    textarea.value = take.transcript || "";
    let saveTimer;
    textarea.addEventListener("input", () => {
      clearTimeout(saveTimer);
      saveTimer = setTimeout(async () => { take.transcript = textarea.value.trim(); await put(take); say("Transcript saved locally."); }, 450);
    });
    const base = `${safeName(take.topic)}--${safeName(take.setTitle)}--Q${take.questionNumber}--${stamp(take.createdAt)}`;
    article.querySelector("[data-audio]").addEventListener("click", () => download(take.audio, `${base}.${extensionFor(take.mimeType)}`));
    article.querySelector("[data-text]").addEventListener("click", () => download(new Blob([take.transcript || "No transcript was saved.\n"], { type: "text/plain;charset=utf-8" }), `${base}--transcript.txt`));
    article.querySelector("[data-delete]").addEventListener("click", async () => {
      if (!confirm("Delete this recording and its transcript from this browser? This cannot be undone unless it is in a backup.")) return;
      URL.revokeObjectURL(url);
      await remove(take.id);
      await refresh();
      say("Recording deleted.");
    });
    return article;
  }

  async function refresh() {
    const takes = await getAll();
    playbackUrls.forEach(url => URL.revokeObjectURL(url));
    playbackUrls = [];
    document.querySelectorAll(".recording-panel").forEach(panel => {
      const list = panel.querySelector(".takes");
      const relevant = takes.filter(take => take.questionKey === panel.dataset.questionKey).sort((a, b) => b.createdAt.localeCompare(a.createdAt));
      list.replaceChildren(...relevant.map(renderTake));
      panel.querySelector(".take-total").textContent = relevant.length ? `${relevant.length} saved ${relevant.length === 1 ? "take" : "takes"}` : "No saved takes yet";
    });
    await updateStorage(takes);
  }

  async function updateStorage(takes = null) {
    const status = document.querySelector("#storage-status");
    const fill = document.querySelector("#storage-meter-fill");
    const list = takes || await getAll();
    const audioBytes = list.reduce((sum, take) => sum + (take.audio?.size || 0), 0);
    const estimate = await navigator.storage?.estimate?.();
    if (estimate?.quota) {
      const percent = Math.min(100, estimate.usage / estimate.quota * 100);
      fill.style.width = `${Math.max(percent, .5)}%`;
      status.textContent = `${list.length} takes (${humanBytes(audioBytes)} audio); this site uses about ${humanBytes(estimate.usage)} of ${humanBytes(estimate.quota)} available browser storage.`;
    } else status.textContent = `${list.length} takes use ${humanBytes(audioBytes)}. This browser does not report its storage allowance.`;
  }

  const crcTable = (() => Array.from({ length: 256 }, (_, n) => { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; return c >>> 0; }))();
  function crc32(bytes) { let crc = 0xffffffff; for (const byte of bytes) crc = crcTable[(crc ^ byte) & 255] ^ (crc >>> 8); return (crc ^ 0xffffffff) >>> 0; }
  const u16 = value => new Uint8Array([value & 255, value >>> 8 & 255]);
  const u32 = value => new Uint8Array([value & 255, value >>> 8 & 255, value >>> 16 & 255, value >>> 24 & 255]);
  const join = arrays => { const out = new Uint8Array(arrays.reduce((n, a) => n + a.length, 0)); let at = 0; arrays.forEach(a => { out.set(a, at); at += a.length; }); return out; };
  async function makeZip(files) {
    const encoder = new TextEncoder(), locals = [], centrals = []; let offset = 0;
    for (const file of files) {
      const name = encoder.encode(file.name), data = new Uint8Array(await file.blob.arrayBuffer()), crc = crc32(data);
      const local = join([u32(0x04034b50), u16(20), u16(0x0800), u16(0), u16(0), u16(0), u32(crc), u32(data.length), u32(data.length), u16(name.length), u16(0), name, data]);
      const central = join([u32(0x02014b50), u16(20), u16(20), u16(0x0800), u16(0), u16(0), u16(0), u32(crc), u32(data.length), u32(data.length), u16(name.length), u16(0), u16(0), u16(0), u16(0), u32(0), u32(offset), name]);
      locals.push(local); centrals.push(central); offset += local.length;
    }
    const directory = join(centrals);
    const end = join([u32(0x06054b50), u16(0), u16(0), u16(files.length), u16(files.length), u32(directory.length), u32(offset), u16(0)]);
    return new Blob([...locals, directory, end], { type: "application/zip" });
  }

  async function exportAll() {
    const takes = await getAll();
    if (!takes.length) { say("There are no recordings to download.", true); return; }
    say(`Preparing ${takes.length} recordings. Large libraries may take a moment…`);
    const manifest = { format: "kooshky-speaking-recordings", version: 1, exportedAt: new Date().toISOString(), recordings: [] };
    const files = [];
    for (const take of takes) {
      const base = `${safeName(take.topic)}--${safeName(take.setTitle)}--Q${take.questionNumber}--${stamp(take.createdAt)}--${take.id.slice(0, 8)}`;
      const audioName = `recordings/${base}.${extensionFor(take.mimeType)}`;
      const transcriptName = `transcripts/${base}.txt`;
      files.push({ name: audioName, blob: take.audio });
      files.push({ name: transcriptName, blob: new Blob([take.transcript || ""], { type: "text/plain;charset=utf-8" }) });
      manifest.recordings.push({ ...take, audio: undefined, audioName, transcriptName });
    }
    files.unshift({ name: "manifest.json", blob: new Blob([JSON.stringify(manifest, null, 2)], { type: "application/json" }) });
    try {
      const zip = await makeZip(files);
      download(zip, `Kooshky-Speaking-Recordings--${stamp(new Date())}.zip`);
      say(`Downloaded a backup containing ${takes.length} recordings. Keep it somewhere safe.`);
    } catch (error) { say(`Could not create the backup: ${error.message}`, true); }
  }

  function readZip(buffer) {
    const bytes = new Uint8Array(buffer), view = new DataView(buffer), decoder = new TextDecoder();
    const files = new Map(); let at = 0;
    while (at + 30 <= bytes.length && view.getUint32(at, true) === 0x04034b50) {
      const method = view.getUint16(at + 8, true), size = view.getUint32(at + 18, true), nameLength = view.getUint16(at + 26, true), extraLength = view.getUint16(at + 28, true);
      if (method !== 0) throw new Error("This ZIP uses compression this importer does not support. Load a ZIP exported by this Speaking Pack.");
      const nameStart = at + 30, dataStart = nameStart + nameLength + extraLength;
      files.set(decoder.decode(bytes.slice(nameStart, nameStart + nameLength)), bytes.slice(dataStart, dataStart + size));
      at = dataStart + size;
    }
    return files;
  }

  async function importZip(file) {
    try {
      say("Checking backup…");
      const files = readZip(await file.arrayBuffer());
      if (!files.has("manifest.json")) throw new Error("manifest.json is missing.");
      const manifest = JSON.parse(new TextDecoder().decode(files.get("manifest.json")));
      if (manifest.format !== "kooshky-speaking-recordings" || manifest.version !== 1 || !Array.isArray(manifest.recordings)) throw new Error("This is not a supported Kooshky Speaking backup.");
      let imported = 0, skipped = 0;
      const existing = new Set((await getAll()).map(take => take.id));
      for (const item of manifest.recordings) {
        const audio = files.get(item.audioName);
        if (!audio || existing.has(item.id)) { skipped++; continue; }
        const transcriptBytes = files.get(item.transcriptName);
        await put({ ...item, transcript: transcriptBytes ? new TextDecoder().decode(transcriptBytes) : item.transcript || "", audio: new Blob([audio], { type: item.mimeType || "audio/webm" }) });
        imported++;
      }
      await refresh();
      say(`Loaded ${imported} recordings as local saves${skipped ? `; skipped ${skipped} duplicates or incomplete entries` : ""}. They will be included in future backups.`);
    } catch (error) {
      say(error?.name === "QuotaExceededError" ? "The backup could not be loaded because browser storage is full. Existing recordings were kept." : `Could not load this backup: ${error.message}`, true);
    }
  }

  function addPanels() {
    document.querySelectorAll(".interview-set").forEach((set, setIndex) => {
      set.querySelectorAll(".question-card").forEach((card, questionIndex) => {
        const details = questionDetails(card, setIndex, questionIndex);
        const panel = document.createElement("section");
        panel.className = "recording-panel";
        panel.dataset.questionKey = details.questionKey;
        panel.innerHTML = `<div class="recording-actions"><button class="record-button" type="button">Record a 45-second answer</button><span class="recording-countdown" aria-live="polite"></span><span class="take-total">No saved takes yet</span></div><div class="takes"></div>`;
        const button = panel.querySelector(".record-button");
        button.addEventListener("click", () => active?.button === button ? stopRecording() : startRecording(button, details, panel));
        card.append(panel);
      });
    });
  }

  document.querySelector("#download-recordings").addEventListener("click", exportAll);
  document.querySelector("#import-recordings").addEventListener("change", event => { const file = event.target.files[0]; if (file) importZip(file); event.target.value = ""; });
  document.querySelector("#request-persistence").addEventListener("click", async () => {
    if (!navigator.storage?.persist) { say("Persistent-storage requests are unavailable in this browser. Keep regular ZIP backups.", true); return; }
    const granted = await navigator.storage.persist();
    say(granted ? "The browser granted persistent storage. Clearing site data can still erase recordings, so keep backups." : "The browser did not grant persistent storage. Keep regular ZIP backups.", !granted);
  });
  document.querySelector("#clear-recordings").addEventListener("click", async () => {
    if (active) { say("Stop and save the current recording before clearing the voice library.", true); return; }
    if (!confirm("Delete ALL locally saved Speaking Pack recordings and transcripts for every topic on this browser? Download a backup first. This cannot be undone.")) return;
    if (!confirm("Final confirmation: permanently clear the entire local voice library?")) return;
    await clear();
    await refresh();
    say("All locally stored recordings and transcripts have been cleared.");
  });

  addPanels();
  refreshMicrophones().catch(() => {});
  navigator.mediaDevices?.addEventListener?.("devicechange", () => refreshMicrophones().catch(() => {}));
  openDb().then(refresh).catch(error => say(`The local recording library could not open: ${error.message}`, true));
})();
