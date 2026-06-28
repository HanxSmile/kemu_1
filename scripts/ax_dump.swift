import AppKit
import ApplicationServices
import Foundation

struct Node: Encodable {
    var role: String?
    var roleDescription: String?
    var title: String?
    var description: String?
    var value: String?
    var identifier: String?
    var enabled: Bool?
    var position: [Double]?
    var size: [Double]?
    var children: [Node] = []
}

func attr(_ element: AXUIElement, _ name: String) -> AnyObject? {
    var value: AnyObject?
    let result = AXUIElementCopyAttributeValue(element, name as CFString, &value)
    return result == .success ? value : nil
}

func stringAttr(_ element: AXUIElement, _ name: String) -> String? {
    guard let value = attr(element, name) else { return nil }
    if let str = value as? String { return str }
    if let num = value as? NSNumber { return num.stringValue }
    return nil
}

func boolAttr(_ element: AXUIElement, _ name: String) -> Bool? {
    guard let value = attr(element, name) as? NSNumber else { return nil }
    return value.boolValue
}

func pointAttr(_ element: AXUIElement, _ name: String) -> [Double]? {
    guard let value = attr(element, name) else { return nil }
    let ax = value as! AXValue
    var point = CGPoint.zero
    if AXValueGetValue(ax, .cgPoint, &point) {
        return [Double(point.x), Double(point.y)]
    }
    return nil
}

func sizeAttr(_ element: AXUIElement, _ name: String) -> [Double]? {
    guard let value = attr(element, name) else { return nil }
    let ax = value as! AXValue
    var size = CGSize.zero
    if AXValueGetValue(ax, .cgSize, &size) {
        return [Double(size.width), Double(size.height)]
    }
    return nil
}

func children(_ element: AXUIElement) -> [AXUIElement] {
    guard let raw = attr(element, kAXChildrenAttribute) else { return [] }
    return (raw as? [AXUIElement]) ?? []
}

func walk(_ element: AXUIElement, depth: Int = 0, maxDepth: Int = 20) -> Node {
    var node = Node(
        role: stringAttr(element, kAXRoleAttribute),
        roleDescription: stringAttr(element, kAXRoleDescriptionAttribute),
        title: stringAttr(element, kAXTitleAttribute),
        description: stringAttr(element, kAXDescriptionAttribute),
        value: stringAttr(element, kAXValueAttribute),
        identifier: stringAttr(element, kAXIdentifierAttribute),
        enabled: boolAttr(element, kAXEnabledAttribute),
        position: pointAttr(element, kAXPositionAttribute),
        size: sizeAttr(element, kAXSizeAttribute),
        children: []
    )
    if depth < maxDepth {
        node.children = children(element).map { walk($0, depth: depth + 1, maxDepth: maxDepth) }
    }
    return node
}

let targetArg = CommandLine.arguments.dropFirst().first ?? "com.jxedt.moto"
let pid: pid_t
if let explicitPid = Int32(targetArg) {
    pid = explicitPid
} else {
    let apps = NSWorkspace.shared.runningApplications
    guard let app = apps.first(where: { running in
        running.bundleIdentifier == targetArg
            || running.localizedName == targetArg
            || running.bundleURL?.lastPathComponent == targetArg
            || running.bundleURL?.path == targetArg
            || running.executableURL?.lastPathComponent == targetArg
    }) else {
        fputs("Application not running: \(targetArg)\n", stderr)
        let names = apps.compactMap { app -> String? in
            guard let name = app.localizedName else { return nil }
            return "\(name) | \(app.bundleIdentifier ?? "-") | \(app.executableURL?.lastPathComponent ?? "-")"
        }.sorted().joined(separator: "\n")
        fputs(names + "\n", stderr)
        exit(2)
    }
    pid = app.processIdentifier
}

let appElement = AXUIElementCreateApplication(pid)
let windows = (attr(appElement, kAXWindowsAttribute) as? [AXUIElement]) ?? []
let targetElement = windows.first ?? appElement
let root = walk(targetElement)

let encoder = JSONEncoder()
encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
let data = try encoder.encode(root)
FileHandle.standardOutput.write(data)
FileHandle.standardOutput.write("\n".data(using: .utf8)!)
