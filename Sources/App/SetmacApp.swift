import SwiftUI

@main
struct SetmacApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate

    var body: some Scene {
        Window("setmac", id: "main") {
            ContentView()
        }
        .windowStyle(.automatic)
        .defaultSize(width: 960, height: 640)
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate, @unchecked Sendable {
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        // A packaged app gets its icon from AppIcon.icns. Under `swift run` there is no
        // bundle, so load icon.png from the SwiftPM resources instead of the generic icon.
        if Bundle.main.object(forInfoDictionaryKey: "CFBundleIconFile") == nil,
           let url = Bundle.module.url(forResource: "icon", withExtension: "png"),
           let image = NSImage(contentsOf: url) {
            NSApp.applicationIconImage = image
        }
        NSApp.activate()
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        true
    }
}
