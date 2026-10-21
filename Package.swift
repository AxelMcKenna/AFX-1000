// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "RMXLab",
    platforms: [.macOS(.v14)],
    products: [.executable(name: "RMXLab", targets: ["RMXLab"])],
    targets: [.executableTarget(name: "RMXLab")]
)
