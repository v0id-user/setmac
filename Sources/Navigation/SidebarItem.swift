import SwiftUI

enum SidebarItem: Hashable, Identifiable {
    case overview
    case category(ToolCategory)
    case configs
    case about

    var id: String {
        switch self {
        case .overview: "overview"
        case .category(let cat): "cat-\(cat.rawValue)"
        case .configs: "configs"
        case .about: "about"
        }
    }

    var title: String {
        switch self {
        case .overview: "Overview"
        case .category(let cat): cat.displayName
        case .configs: "Dotfiles"
        case .about: "About"
        }
    }

    var icon: String {
        switch self {
        case .overview: "square.grid.2x2"
        case .category(let cat): cat.icon
        case .configs: "doc.on.doc"
        case .about: "info.circle"
        }
    }

    var iconColor: Color {
        switch self {
        case .overview: .blue
        case .category(let cat): cat.color
        case .configs: .gray
        case .about: .blue
        }
    }
}
