import SwiftUI

struct AuthPasswordSheetView: View {
    let request: AuthRequest
    let onSubmit: (String) -> Void
    let onCancel: () -> Void

    @State private var password = ""
    @FocusState private var isPasswordFocused: Bool

    var body: some View {
        VStack(spacing: 20) {
            Text("Admin Password Required")
                .font(.headline)

            Text(request.message)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)

            SecureField("Password", text: $password)
                .textFieldStyle(.roundedBorder)
                .focused($isPasswordFocused)
                .onSubmit { submit() }

            HStack(spacing: 12) {
                Button("Cancel") {
                    onCancel()
                }
                .keyboardShortcut(.cancelAction)

                Button("Submit") {
                    submit()
                }
                .keyboardShortcut(.defaultAction)
                .disabled(password.isEmpty)
            }
        }
        .padding(24)
        .frame(minWidth: 320)
        .onAppear {
            isPasswordFocused = true
        }
    }

    private func submit() {
        let p = password
        password = ""
        onSubmit(p)
    }
}
