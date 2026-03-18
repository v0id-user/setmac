// swift-tools-version: 6.2

import PackageDescription

let package = Package(
    name: "Rig",
    platforms: [.macOS(.v26)],
    targets: [
        .executableTarget(
            name: "Rig",
            path: "Sources",
            resources: [
                .process("../Resources/Assets.xcassets"),
            ]
        )
    ]
)
