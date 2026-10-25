const $ = id => document.getElementById(id);
const controls = {
  low: $('low'), mid: $('mid'), high: $('high'),
  mix: $('mix'), feedback: $('feedback'), bpm: $('bpm'), division: $('division')
};

let context;
let stream;
let source;
let fx;
let outputGain;
let running = false;

function setStatus(text, on = false) {
  $('statusText').textContent = text;
  $('statusDot').classList.toggle('on', on);
  $('startButton').classList.toggle('running', on);
  $('startLabel').textContent = on ? 'STOP AUDIO' : 'START AUDIO';
}

function dbToGain(db) { return 10 ** (Number(db) / 20); }

function updateParam(name, value) {
  if (!fx || !context) return;
  fx.parameters.get(name).setTargetAtTime(value, context.currentTime, 0.012);
}

function syncControls() {
  for (const band of ['low', 'mid', 'high']) {
    $(`${band}Value`).textContent = `${controls[band].value} dB`;
    updateParam(`${band}Gain`, dbToGain(controls[band].value));
  }
  $('mixValue').textContent = `${controls.mix.value}%`;
  $('feedbackValue').textContent = `${controls.feedback.value}%`;
  updateParam('mix', Number(controls.mix.value) / 100);
  updateParam('feedback', Number(controls.feedback.value) / 100);
  const bpm = Math.max(60, Math.min(200, Number(controls.bpm.value) || 120));
  controls.bpm.value = bpm;
  updateParam('delaySeconds', 60 / bpm * Number(controls.division.value));
}

async function refreshDevices() {
  if (!navigator.mediaDevices?.enumerateDevices) return;
  const devices = await navigator.mediaDevices.enumerateDevices();
  populateSelect($('inputDevice'), devices.filter(d => d.kind === 'audioinput'), 'System default input');
  populateSelect($('outputDevice'), devices.filter(d => d.kind === 'audiooutput'), 'System default output');
}

function populateSelect(select, devices, fallback) {
  const previous = select.value;
  select.replaceChildren(new Option(fallback, ''));
  devices.forEach((device, i) => select.add(new Option(device.label || `Audio device ${i + 1}`, device.deviceId)));
  if ([...select.options].some(option => option.value === previous)) select.value = previous;
}

async function stopAudio() {
  running = false;
  if (source) source.disconnect();
  if (fx) fx.disconnect();
  if (outputGain) outputGain.disconnect();
  if (stream) stream.getTracks().forEach(track => track.stop());
  if (context && context.state !== 'closed') await context.close();
  context = source = fx = outputGain = stream = undefined;
  $('latencyReadout').textContent = '— ms';
  setStatus('AUDIO STOPPED');
}

async function startAudio() {
  if (running) return stopAudio();
  if (!navigator.mediaDevices?.getUserMedia || !window.AudioWorkletNode) {
    setStatus('USE A RECENT BROWSER');
    return;
  }
  $('startButton').disabled = true;
  setStatus('CONNECTING AUDIO…');
  try {
    const inputId = $('inputDevice').value;
    const audio = { channelCount: { ideal: 2 }, echoCancellation: false, noiseSuppression: false, autoGainControl: false };
    if (inputId) audio.deviceId = { exact: inputId };
    stream = await navigator.mediaDevices.getUserMedia({ audio, video: false });
    context = new AudioContext({ latencyHint: 'interactive' });
    await context.audioWorklet.addModule('./isolator-echo.js');
    source = context.createMediaStreamSource(stream);
    fx = new AudioWorkletNode(context, 'isolator-echo', { numberOfInputs: 1, numberOfOutputs: 1, outputChannelCount: [2] });
    outputGain = context.createGain();
    outputGain.gain.value = 0.8;
    source.connect(fx).connect(outputGain).connect(context.destination);
    if ($('outputDevice').value && typeof context.setSinkId === 'function') await context.setSinkId($('outputDevice').value);
    await context.resume();
    syncControls();
    running = true;
    const latencyMs = Math.round((context.baseLatency || 0) * 1000);
    $('latencyReadout').textContent = `${latencyMs} ms BASE`;
    setStatus('AUDIO RUNNING', true);
    await refreshDevices();
  } catch (error) {
    await stopAudio();
    setStatus(error.name === 'NotAllowedError' ? 'MIC ACCESS BLOCKED' : 'AUDIO START FAILED');
    console.error(error);
  } finally {
    $('startButton').disabled = false;
  }
}

Object.values(controls).forEach(control => control.addEventListener('input', syncControls));
$('startButton').addEventListener('click', startAudio);
$('inputDevice').addEventListener('focus', refreshDevices);
$('outputDevice').addEventListener('focus', refreshDevices);
$('inputDevice').addEventListener('change', async () => {
  if (running) { await stopAudio(); await startAudio(); }
});
$('outputDevice').addEventListener('change', async () => {
  if (context && typeof context.setSinkId === 'function') {
    try { await context.setSinkId($('outputDevice').value || ''); }
    catch (error) { console.error(error); setStatus('OUTPUT DEVICE CHANGE FAILED', true); }
  }
});
syncControls();
if (typeof AudioContext === 'undefined' || typeof AudioContext.prototype.setSinkId !== 'function') {
  $('outputDevice').disabled = true;
  $('outputDevice').options[0].textContent = 'System default output (select in macOS Audio settings)';
}
refreshDevices();
