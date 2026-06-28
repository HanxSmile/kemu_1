import ApplicationServices
import Foundation

func mouse(_ type: CGEventType, _ point: CGPoint) {
    CGEvent(mouseEventSource: nil, mouseType: type, mouseCursorPosition: point, mouseButton: .left)?.post(tap: .cghidEventTap)
}

let x1 = Double(CommandLine.arguments.dropFirst().first ?? "1076") ?? 1076
let y1 = Double(CommandLine.arguments.dropFirst().dropFirst().first ?? "-779") ?? -779
let x2 = Double(CommandLine.arguments.dropFirst().dropFirst().dropFirst().first ?? "676") ?? 676
let y2 = Double(CommandLine.arguments.dropFirst().dropFirst().dropFirst().dropFirst().first ?? "-779") ?? -779

let start = CGPoint(x: x1, y: y1)
let end = CGPoint(x: x2, y: y2)
mouse(.leftMouseDown, start)
for step in 1...12 {
    let t = Double(step) / 12.0
    let p = CGPoint(x: start.x + (end.x - start.x) * t, y: start.y + (end.y - start.y) * t)
    mouse(.leftMouseDragged, p)
    usleep(15_000)
}
mouse(.leftMouseUp, end)
usleep(600_000)
