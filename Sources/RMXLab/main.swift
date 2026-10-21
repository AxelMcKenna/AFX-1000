import AVFAudio
import SwiftUI

@main
struct RMXLabApp: App {
    @StateObject private var audio = AudioController()

    var body: some Scene {
        WindowGroup {
            ContentView(audio: audio)
                .frame(minWidth: 680, minHeight: 570)
        }
        .windowResizability(.contentSize)
    }
}

final class AudioController: ObservableObject {
    @Published var isRunning = false
    @Published var status = "Stopped"
    @Published var sampleRate = "—"
    @Published var inputChannels = 0
    @Published var outputChannels = 0
    @Published var low = 0.0 { didSet { processor.setBandGains(low: low, mid: mid, high: high) } }
    @Published var mid = 0.0 { didSet { processor.setBandGains(low: low, mid: mid, high: high) } }
    @Published var high = 0.0 { didSet { processor.setBandGains(low: low, mid: mid, high: high) } }
    @Published var echoMix = 0.0 { didSet { processor.echoMix = Float(echoMix / 100) } }
    @Published var feedback = 32.0 { didSet { processor.feedback = Float(feedback / 100) } }
    @Published var bpm = 120.0 { didSet { processor.bpm = Float(bpm) } }
    @Published var division = 0.5 { didSet { processor.division = Float(division) } }

    private let engine = AVAudioEngine()
    private let player = AVAudioPlayerNode()
    private let processor = StereoProcessor()
    private var tapInstalled = false

    func start() {
        guard !isRunning else { return }
        let input = engine.inputNode
        let format = input.inputFormat(forBus: 0)
        guard format.channelCount >= 1, format.sampleRate > 0 else {
            status = "No audio input available. Connect an interface and select it in Audio MIDI Setup."
            return
        }
        engine.attach(player)
        engine.connect(player, to: engine.mainMixerNode, format: format)
        processor.configure(sampleRate: format.sampleRate, channels: Int(format.channelCount))
        do {
            input.installTap(onBus: 0, bufferSize: 256, format: format) { [weak self] buffer, _ in
                guard let self, let processed = self.processor.process(buffer) else { return }
                self.player.scheduleBuffer(processed, completionHandler: nil)
            }
            tapInstalled = true
            try engine.start()
            player.play()
            isRunning = true
            sampleRate = "\(Int(format.sampleRate / 1000)) kHz"
            inputChannels = Int(format.channelCount)
            outputChannels = Int(engine.outputNode.outputFormat(forBus: 0).channelCount)
            status = "Running • system default audio device"
        } catch {
            if tapInstalled { input.removeTap(onBus: 0); tapInstalled = false }
            engine.stop()
            if engine.attachedNodes.contains(player) { engine.detach(player) }
            status = "Could not start audio: \(error.localizedDescription)"
        }
    }

    func stop() {
        if tapInstalled { engine.inputNode.removeTap(onBus: 0); tapInstalled = false }
        player.stop()
        engine.stop()
        if engine.attachedNodes.contains(player) { engine.detach(player) }
        isRunning = false
        status = "Stopped"
    }

    deinit { stop() }
}

/// Block-based stereo FX. The lock is held only while copying a handful of controls;
/// the delay line and filter state stay on the audio callback.
final class StereoProcessor {
    private let lock = NSLock()
    private var gains: (Float, Float, Float) = (1, 1, 1)
    var echoMix: Float = 0
    var feedback: Float = 0.32
    var bpm: Float = 120
    var division: Float = 0.5
    private var sampleRate = 48_000.0
    private var channels = 2
    private var delay: [[Float]] = [[], []]
    private var writeIndex = 0
    private var lowState: [Float] = [0, 0]
    private var midState: [Float] = [0, 0]

    func configure(sampleRate: Double, channels: Int) {
        self.sampleRate = sampleRate
        self.channels = max(1, min(2, channels))
        let size = max(1, Int(sampleRate * 2.1))
        delay = Array(repeating: Array(repeating: 0, count: size), count: 2)
        writeIndex = 0
        lowState = [0, 0]
        midState = [0, 0]
    }

    func setBandGains(low: Double, mid: Double, high: Double) {
        lock.lock()
        gains = (dbGain(low), dbGain(mid), dbGain(high))
        lock.unlock()
    }

    private func dbGain(_ db: Double) -> Float { Float(pow(10, db / 20)) }

    func process(_ input: AVAudioPCMBuffer) -> AVAudioPCMBuffer? {
        guard let src = input.floatChannelData else { return nil }
        let count = Int(input.frameLength)
        guard let out = AVAudioPCMBuffer(pcmFormat: input.format, frameCapacity: input.frameLength),
              let dst = out.floatChannelData else { return nil }
        lock.lock(); let band = gains; lock.unlock()

        let mix = max(0, min(1, echoMix))
        let fb = max(0, min(0.88, feedback))
        let delayFrames = max(1, min(delay[0].count - 1, Int(sampleRate * 60 / Double(max(40, min(240, bpm))) * Double(max(0.125, min(2, division))))))
        let aLow = Float(1 - exp(-2 * Double.pi * 250 / sampleRate))
        let aMid = Float(1 - exp(-2 * Double.pi * 2200 / sampleRate))

        for frame in 0..<count {
            let idx = writeIndex
            let read = (idx - delayFrames + delay[0].count) % delay[0].count
            for ch in 0..<2 {
                let source = ch < channels ? src[ch][frame] : src[0][frame]
                lowState[ch] += aLow * (source - lowState[ch])
                midState[ch] += aMid * (source - midState[ch])
                let low = lowState[ch]
                let mid = midState[ch] - low
                let high = source - midState[ch]
                let dry = low * band.0 + mid * band.1 + high * band.2
                let echo = delay[ch][read]
                let wet = dry * (1 - mix) + echo * mix
                dst[ch][frame] = max(-1, min(1, wet))
                delay[ch][idx] = dry + echo * fb
            }
            writeIndex = (writeIndex + 1) % delay[0].count
        }
        out.frameLength = input.frameLength
        return out
    }
}

struct ContentView: View {
    @ObservedObject var audio: AudioController

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            HStack(alignment: .firstTextBaseline) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("RMX Lab").font(.system(size: 30, weight: .bold, design: .rounded))
                    Text("Stereo isolator + beat echo • macOS prototype").foregroundStyle(.secondary)
                }
                Spacer()
                Button(audio.isRunning ? "Stop Audio" : "Start Audio") {
                    audio.isRunning ? audio.stop() : audio.start()
                }
                .buttonStyle(.borderedProminent)
                .tint(audio.isRunning ? .red : .accentColor)
            }

            GroupBox("3-band isolator") {
                HStack(spacing: 18) {
                    bandControl("LOW", value: $audio.low)
                    bandControl("MID", value: $audio.mid)
                    bandControl("HIGH", value: $audio.high)
                }.padding(.top, 6)
            }

            GroupBox("Echo") {
                VStack(spacing: 14) {
                    HStack { Text("Wet mix"); Slider(value: $audio.echoMix, in: 0...100); Text("\(Int(audio.echoMix))% ").monospacedDigit().frame(width: 46, alignment: .trailing) }
                    HStack { Text("Feedback"); Slider(value: $audio.feedback, in: 0...88); Text("\(Int(audio.feedback))%").monospacedDigit().frame(width: 46, alignment: .trailing) }
                    HStack {
                        Text("Tempo"); Slider(value: $audio.bpm, in: 60...200); Text("\(Int(audio.bpm)) BPM").monospacedDigit().frame(width: 75, alignment: .trailing)
                        Picker("Beat", selection: $audio.division) {
                            Text("1/4").tag(0.25); Text("1/2").tag(0.5); Text("1 beat").tag(1.0); Text("2 beats").tag(2.0)
                        }.frame(width: 120)
                    }
                }.padding(.top, 6)
            }

            HStack(spacing: 12) {
                Circle().fill(audio.isRunning ? .green : .gray).frame(width: 9, height: 9)
                Text(audio.status).lineLimit(1)
                Spacer()
                Text("\(audio.sampleRate) • \(audio.inputChannels) in / \(audio.outputChannels) out").foregroundStyle(.secondary).font(.caption)
            }.font(.callout)

            Text("Prototype note: audio uses the macOS default input/output. Use headphones while setting levels; the current pass-through path adds buffering latency and is for routing checks, not a performance-ready effect.")
                .font(.caption).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
        }
        .padding(24)
    }

    private func bandControl(_ title: String, value: Binding<Double>) -> some View {
        VStack(spacing: 8) {
            Text(title).font(.caption.weight(.semibold)).foregroundStyle(.secondary)
            Slider(value: value, in: -24...6)
            Text("\(Int(value.wrappedValue)) dB").font(.system(.body, design: .monospaced)).frame(width: 58)
        }.frame(maxWidth: .infinity)
    }
}
