// swift-tools-version: 6.2

import PackageDescription

let package = Package(
    name: "Setmac",
    platforms: [.macOS(.v26)],
    targets: [
        .executableTarget(
            name: "Setmac",
            path: "Sources",
            resources: [
                .process("../Resources/Assets.xcassets"),
            ]
        )
    ]
)
