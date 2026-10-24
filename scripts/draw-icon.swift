// Draws the setmac app icon: a grainy paper-to-graphite gradient with one small
// line drawing. Variants: paper (laptop), fog (sunrise), sprout (seedling).
// Usage: swift scripts/draw-icon.swift [--seed N] [variant] [output.png]   (writes 1024x1024)
// The grain comes from a seeded generator, so the same seed always gives the same pixels.

import AppKit

var seed: UInt64 = 0x5E7_AC00
var positional: [String] = []
var argIterator = CommandLine.arguments.dropFirst().makeIterator()
while let arg = argIterator.next() {
    if arg == "--seed" {
        guard let value = argIterator.next(), let parsed = UInt64(value) else { fatalError("--seed needs a number") }
        seed = parsed
    } else {
        positional.append(arg)
    }
}
let variant = positional.count > 0 ? positional[0] : "sprout"
let output = positional.count > 1 ? positional[1] : "Resources/icon.png"
let size = 1024

/// SplitMix64: tiny, fast, and stable across Swift versions, unlike the system generator.
struct SplitMix64: RandomNumberGenerator {
    var state: UInt64
    mutating func next() -> UInt64 {
        state &+= 0x9E37_79B9_7F4A_7C15
        var z = state
        z = (z ^ (z >> 30)) &* 0xBF58_476D_1CE4_E5B9
        z = (z ^ (z >> 27)) &* 0x94D0_49BB_1331_11EB
        return z ^ (z >> 31)
    }
}

guard let ctx = CGContext(
    data: nil, width: size, height: size, bitsPerComponent: 8, bytesPerRow: size * 4,
    space: CGColorSpace(name: CGColorSpace.sRGB)!,
    bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
) else { fatalError("no context") }

// Draw in top-left coordinates.
ctx.translateBy(x: 0, y: CGFloat(size))
ctx.scaleBy(x: 1, y: -1)

func gray(_ v: CGFloat, _ a: CGFloat = 1) -> CGColor { CGColor(srgbRed: v, green: v, blue: v, alpha: a) }
func warm(_ v: CGFloat, _ a: CGFloat = 1) -> CGColor { CGColor(srgbRed: v, green: v * 0.985, blue: v * 0.955, alpha: a) }

// Apple's macOS icon grid: an 824pt body centered on the 1024pt canvas.
let body = CGRect(x: 100, y: 100, width: 824, height: 824)
let bodyPath = CGPath(roundedRect: body, cornerWidth: 186, cornerHeight: 186, transform: nil)

ctx.saveGState()
ctx.setShadow(offset: CGSize(width: 0, height: 12), blur: 28, color: gray(0, 0.28))
ctx.addPath(bodyPath)
ctx.setFillColor(gray(0.9))
ctx.fillPath()
ctx.restoreGState()

ctx.saveGState()
ctx.addPath(bodyPath)
ctx.clip()

let ink: CGColor
switch variant {
case "paper":
    let g = CGGradient(colorsSpace: nil, colors: [gray(0.99), gray(0.93), gray(0.80)] as CFArray, locations: [0, 0.55, 1])!
    ctx.drawRadialGradient(g, startCenter: CGPoint(x: 400, y: 300), startRadius: 0,
                           endCenter: CGPoint(x: 512, y: 512), endRadius: 760, options: [.drawsAfterEndLocation])
    ink = gray(0.16)
case "sprout":
    let g = CGGradient(colorsSpace: nil, colors: [warm(0.985), warm(0.94), warm(0.82)] as CFArray, locations: [0, 0.6, 1])!
    ctx.drawLinearGradient(g, start: CGPoint(x: 512, y: 100), end: CGPoint(x: 512, y: 924), options: [])
    ink = gray(0.18)
default:  // fog
    let g = CGGradient(colorsSpace: nil, colors: [gray(0.98), gray(0.90), gray(0.55), gray(0.17)] as CFArray,
                       locations: [0, 0.42, 0.75, 1])!
    ctx.drawLinearGradient(g, start: CGPoint(x: 512, y: 100), end: CGPoint(x: 512, y: 924), options: [])
    ink = gray(0.14)
}

// Small line drawing, thin charcoal strokes.
ctx.setStrokeColor(ink)
ctx.setLineWidth(11)
ctx.setLineCap(.round)
ctx.setLineJoin(.round)

switch variant {
case "paper":
    // A tiny open laptop, low and a little off-center.
    let screen = CGPath(roundedRect: CGRect(x: 436, y: 540, width: 152, height: 100), cornerWidth: 12, cornerHeight: 12, transform: nil)
    ctx.addPath(screen)
    ctx.move(to: CGPoint(x: 410, y: 662)); ctx.addLine(to: CGPoint(x: 614, y: 662))
    ctx.strokePath()
    ctx.setLineWidth(8)
    ctx.move(to: CGPoint(x: 492, y: 590)); ctx.addLine(to: CGPoint(x: 532, y: 590))  // a quiet cursor
    ctx.strokePath()
case "sprout":
    // A seedling: stem and two leaves.
    ctx.move(to: CGPoint(x: 512, y: 690)); ctx.addCurve(to: CGPoint(x: 512, y: 548), control1: CGPoint(x: 506, y: 640), control2: CGPoint(x: 518, y: 590))
    let left = CGMutablePath()
    left.move(to: CGPoint(x: 512, y: 588))
    left.addCurve(to: CGPoint(x: 432, y: 528), control1: CGPoint(x: 488, y: 548), control2: CGPoint(x: 456, y: 530))
    left.addCurve(to: CGPoint(x: 512, y: 588), control1: CGPoint(x: 444, y: 574), control2: CGPoint(x: 480, y: 594))
    let right = CGMutablePath()
    right.move(to: CGPoint(x: 512, y: 560))
    right.addCurve(to: CGPoint(x: 600, y: 488), control1: CGPoint(x: 534, y: 512), control2: CGPoint(x: 568, y: 490))
    right.addCurve(to: CGPoint(x: 512, y: 560), control1: CGPoint(x: 592, y: 534), control2: CGPoint(x: 552, y: 562))
    ctx.addPath(left); ctx.addPath(right)
    ctx.move(to: CGPoint(x: 452, y: 692)); ctx.addLine(to: CGPoint(x: 572, y: 692))  // ground
    ctx.strokePath()
default:
    // A small sun rising over the horizon, drawn in light ink on the dark band.
    ctx.setStrokeColor(gray(0.96))
    ctx.addArc(center: CGPoint(x: 512, y: 640), radius: 64, startAngle: .pi, endAngle: 0, clockwise: false)
    ctx.move(to: CGPoint(x: 400, y: 640)); ctx.addLine(to: CGPoint(x: 624, y: 640))
    ctx.setLineWidth(10)
    ctx.strokePath()
    ctx.setLineWidth(8)
    for angle in stride(from: 200.0, through: 340.0, by: 35.0) {
        let a = angle * .pi / 180
        ctx.move(to: CGPoint(x: 512 + cos(a) * 92, y: 640 + sin(a) * 92))
        ctx.addLine(to: CGPoint(x: 512 + cos(a) * 112, y: 640 + sin(a) * 112))
    }
    ctx.strokePath()
}
ctx.restoreGState()

// Thin inner edge.
ctx.addPath(CGPath(roundedRect: body.insetBy(dx: 1.5, dy: 1.5), cornerWidth: 185, cornerHeight: 185, transform: nil))
ctx.setStrokeColor(gray(1, 0.5))
ctx.setLineWidth(3)
ctx.strokePath()

// Film grain: per-pixel luminance noise inside the body.
let pixels = ctx.data!.bindMemory(to: UInt8.self, capacity: size * size * 4)
var rng = SplitMix64(state: seed)
for i in 0..<(size * size) {
    let o = i * 4
    let alpha = Int(pixels[o + 3])
    guard alpha == 255 else { continue }
    let n = Int.random(in: -14...14, using: &rng)
    for c in 0..<3 { pixels[o + c] = UInt8(max(0, min(255, Int(pixels[o + c]) + n))) }
}

guard let image = ctx.makeImage() else { fatalError("no image") }
let rep = NSBitmapImageRep(cgImage: image)
try rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: output))
print("Wrote \(output)")
