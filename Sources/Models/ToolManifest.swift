import SwiftUI

// MARK: - Codable types matching tools.json

struct ToolManifest: Codable {
    let version: String
    let name: String
    let description: String
    let author: String
    let tools: [ToolDefinition]
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

    enum CodingKeys: String, CodingKey {
        case id, name, description, category, icon, install, check, configs
        case iconColor = "icon_color"
        case dependsOn = "depends_on"
    }

    static func == (lhs: ToolDefinition, rhs: ToolDefinition) -> Bool {
        lhs.id == rhs.id
    }

    func hash(into hasher: inout Hasher) {
        hasher.combine(id)
    }

    var swiftColor: Color {
        switch iconColor {
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

// MARK: - Category mapping

enum ToolCategory: String, CaseIterable, Identifiable {
    case essentials
    case cliTools = "cli-tools"
    case applications
    case languages
    case standalone
    case configs

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .essentials: "Essentials"
        case .cliTools: "CLI Tools"
        case .applications: "Applications"
        case .languages: "Languages"
        case .standalone: "Standalone"
        case .configs: "Configs"
        }
    }

    var icon: String {
        switch self {
        case .essentials: "star.fill"
        case .cliTools: "terminal"
        case .applications: "macwindow"
        case .languages: "chevron.left.forwardslash.chevron.right"
        case .standalone: "puzzlepiece.extension"
        case .configs: "gearshape.2"
        }
    }

    var color: Color {
        switch self {
        case .essentials: .blue
        case .cliTools: .green
        case .applications: .purple
        case .languages: .orange
        case .standalone: .teal
        case .configs: .gray
        }
    }
}
