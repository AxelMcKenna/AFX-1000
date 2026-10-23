class IsolatorEcho extends AudioWorkletProcessor {
  static get parameterDescriptors() {
    return [
      { name: 'lowGain', defaultValue: 1, minValue: 0, maxValue: 2 },
      { name: 'midGain', defaultValue: 1, minValue: 0, maxValue: 2 },
      { name: 'highGain', defaultValue: 1, minValue: 0, maxValue: 2 },
      { name: 'mix', defaultValue: 0, minValue: 0, maxValue: 1 },
      { name: 'feedback', defaultValue: 0.32, minValue: 0, maxValue: 0.88 },
      { name: 'delaySeconds', defaultValue: 0.25, minValue: 0.05, maxValue: 2 }
    ];
  }

  constructor() {
    super();
    this.maxDelay = Math.ceil(sampleRate * 2.05);
    this.delay = [new Float32Array(this.maxDelay), new Float32Array(this.maxDelay)];
    this.write = 0;
    this.lowState = [0, 0];
    this.midState = [0, 0];
    this.lowCoeff = 1 - Math.exp(-2 * Math.PI * 250 / sampleRate);
    this.midCoeff = 1 - Math.exp(-2 * Math.PI * 2200 / sampleRate);
  }

  process(inputs, outputs, params) {
    const input = inputs[0];
    const output = outputs[0];
    if (!input?.length || !output?.length) return true;
    const frames = output[0].length;
    const one = name => params[name].length === 1;
    const value = (name, i) => params[name][one(name) ? 0 : i];

    for (let i = 0; i < frames; i++) {
      const lowGain = value('lowGain', i), midGain = value('midGain', i), highGain = value('highGain', i);
      const mix = value('mix', i), feedback = value('feedback', i);
      const delayFrames = Math.max(1, Math.min(this.maxDelay - 1, Math.round(value('delaySeconds', i) * sampleRate)));
      const read = (this.write - delayFrames + this.maxDelay) % this.maxDelay;
      for (let ch = 0; ch < output.length; ch++) {
        const source = input[Math.min(ch, input.length - 1)][i] || 0;
        this.lowState[ch] += this.lowCoeff * (source - this.lowState[ch]);
        this.midState[ch] += this.midCoeff * (source - this.midState[ch]);
        const low = this.lowState[ch];
        const mid = this.midState[ch] - low;
        const high = source - this.midState[ch];
        const dry = low * lowGain + mid * midGain + high * highGain;
        const echo = this.delay[ch][read];
        output[ch][i] = Math.max(-1, Math.min(1, dry * (1 - mix) + echo * mix));
        this.delay[ch][this.write] = dry + echo * feedback;
      }
      this.write = (this.write + 1) % this.maxDelay;
    }
    return true;
  }
}

registerProcessor('isolator-echo', IsolatorEcho);
