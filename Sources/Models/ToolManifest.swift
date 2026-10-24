import SwiftUI

// MARK: - Codable types matching tools.json

struct ToolManifest: Codable {
    let version: String
    let name: String
    let description: String
    let author: String?
    /// Sidebar categories. When absent, the built-in set is used.
    let categories: [CategoryDefinition]?
    let tools: [ToolDefinition]
}

struct CategoryDefinition: Codable {
    let id: String
    let name: String
    let icon: String?
    let color: String?
    let order: Int?
}

struct ToolDefinition: Codable, Identifiable, Hashable {
    let id: String
    let name: String
    let description: String
    let category: String
    let icon: String
    let iconColor: String
    let dependsOn: [String]
    let check: CheckSpec?
    let install: InstallSpec
    let configs: [ConfigSpec]?
    /// Manual step left after install, e.g. granting a permission.
    let postInstall: String?

    enum CodingKeys: String, CodingKey {
        case id, name, description, category, icon, install, check, configs
        case iconColor = "icon_color"
        case dependsOn = "depends_on"
        case postInstall = "post_install"
    }

    static func == (lhs: ToolDefinition, rhs: ToolDefinition) -> Bool {
        lhs.id == rhs.id
    }

    func hash(into hasher: inout Hasher) {
        hasher.combine(id)
    }

    var swiftColor: Color { Color.named(iconColor) }
}

extension Color {
    /// Colors by the names tools.json uses; unknown names are secondary.
    static func named(_ name: String) -> Color {
        switch name {
        case "blue": .blue
        case "orange": .orange
        case "green": .green
        case "red": .red
        case "purple": .purple
        case "cyan": .cyan
        case "yellow": .yellow
        case "pink": .pink
        case "brown": .brown
        case "gray": .gray
        case "teal": .teal
        case "white": .primary
        case "indigo": .indigo
        case "mint": .mint
        default: .secondary
        }
    }
}

struct CheckSpec: Codable {
    let command: String?
    let path: String?
    let versionCommand: String?

    enum CodingKeys: String, CodingKey {
        case command, path
        case versionCommand = "version_command"
    }
}

struct InstallSpec: Codable {
    let method: String
    let target: String?
    let script: String?
    let url: String?
}

struct ConfigSpec: Codable {
    let source: String
    let target: String
    let isDir: Bool?

    enum CodingKeys: String, CodingKey {
        case source, target
        case isDir = "is_dir"
    }
}

// MARK: - Categories

/// A sidebar category. Comes from the manifest's `categories` list, or the built-in
/// set when the manifest has none. Tools in a category nobody defined go to `other`.
struct ToolCategory: Hashable, Identifiable {
    let id: String
    let displayName: String
    let icon: String
    let colorName: String
    let order: Int?

    var color: Color { Color.named(colorName) }

    init(id: String, displayName: String, icon: String, colorName: String, order: Int? = nil) {
        self.id = id
        self.displayName = displayName
        self.icon = icon
        self.colorName = colorName
        self.order = order
    }

    init(_ definition: CategoryDefinition) {
        self.init(
            id: definition.id,
            displayName: definition.name,
            icon: definition.icon ?? "square.grid.2x2",
            colorName: definition.color ?? "gray",
            order: definition.order
        )
    }

    static let builtIn: [ToolCategory] = [
        ToolCategory(id: "essentials", displayName: "Essentials", icon: "star.fill", colorName: "blue"),
        ToolCategory(id: "cli-tools", displayName: "CLI Tools", icon: "terminal", colorName: "green"),
        ToolCategory(id: "applications", displayName: "Applications", icon: "macwindow", colorName: "purple"),
        ToolCategory(id: "languages", displayName: "Languages", icon: "chevron.left.forwardslash.chevron.right", colorName: "orange"),
        ToolCategory(id: "standalone", displayName: "Standalone", icon: "puzzlepiece.extension", colorName: "teal"),
        ToolCategory(id: "configs", displayName: "Configs", icon: "gearshape.2", colorName: "gray"),
        ToolCategory(id: "system", displayName: "macOS Settings", icon: "gearshape", colorName: "secondary"),
    ]

    /// Holds tools whose category is not defined, so they never disappear from the UI.
    static let other = ToolCategory(id: "other", displayName: "Other", icon: "ellipsis.circle", colorName: "gray")
}
