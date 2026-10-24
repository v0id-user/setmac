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
                // Sets the Dock icon under `swift run`, where there is no .app bundle.
                .copy("../Resources/icon.png"),
            ]
        )
    ]
)
