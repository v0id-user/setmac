import SwiftUI

enum SidebarItem: Hashable, Identifiable {
    case overview
    case category(ToolCategory)
    case profile
    case configs
    case about

    var id: String {
        switch self {
        case .overview: "overview"
        case .category(let cat): "cat-\(cat.id)"
        case .profile: "profile"
        case .configs: "configs"
        case .about: "about"
        }
    }

    var title: String {
        switch self {
        case .overview: "Overview"
        case .category(let cat): cat.displayName
        case .profile: "Profile"
        case .configs: "Dotfiles"
        case .about: "About"
        }
    }

    var icon: String {
        switch self {
        case .overview: "square.grid.2x2"
        case .category(let cat): cat.icon
        case .profile: "person.crop.square"
        case .configs: "doc.on.doc"
        case .about: "info.circle"
        }
    }

    var iconColor: Color {
        switch self {
        case .overview: .blue
        case .category(let cat): cat.color
        case .profile: .indigo
        case .configs: .gray
        case .about: .blue
        }
    }
}
