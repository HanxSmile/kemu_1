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

struct TextItem: Encodable {
    var text: String
    var source: String
    var role: String?
    var roleDescription: String?
    var position: [Double]?
    var size: [Double]?
}

struct Record: Encodable {
    var paper: Int
    var index: Int
    var questionKey: String
    var hasImageCandidate: Bool
    var texts: [TextItem]
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

func walk(_ element: AXUIElement, depth: Int = 0, maxDepth: Int = 18) -> Node {
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

func windowRoot(pid: pid_t) -> Node {
    let appElement = AXUIElementCreateApplication(pid)
    let windows = (attr(appElement, kAXWindowsAttribute) as? [AXUIElement]) ?? []
    let targetElement = windows.first ?? appElement
    return walk(targetElement)
}

func addText(_ item: String?, _ source: String, _ node: Node, _ out: inout [TextItem]) {
    guard let raw = item else { return }
    let text = raw.trimmingCharacters(in: .whitespacesAndNewlines)
    guard !text.isEmpty else { return }
    out.append(TextItem(
        text: text,
        source: source,
        role: node.role,
        roleDescription: node.roleDescription,
        position: node.position,
        size: node.size
    ))
}

func flattenTexts(_ node: Node, _ out: inout [TextItem]) {
    addText(node.description, "description", node, &out)
    addText(node.title, "title", node, &out)
    addText(node.value, "value", node, &out)
    for child in node.children {
        flattenTexts(child, &out)
    }
}

func clean(_ text: String) -> String {
    text
        .replacingOccurrences(of: "\u{fffc}", with: "")
        .replacingOccurrences(of: "￼", with: "")
        .trimmingCharacters(in: .whitespacesAndNewlines)
}

func questionKey(_ texts: [TextItem]) -> String {
    let ignored = ["test back", "答题", "背题", "question setting", "题目解析", "试题详解", "点击或上拉加载更多"]
    let candidates = texts.map { clean($0.text) }.filter { text in
        !text.isEmpty
            && !ignored.contains(text)
            && !text.hasPrefix("答案 ")
            && !text.hasPrefix("秒懂技巧")
            && !text.hasPrefix("速记口诀")
            && !text.hasPrefix("相关考点")
            && !text.hasPrefix("板书讲题")
            && !text.contains("驾校一点通")
    }
    if let question = candidates.first(where: { $0.contains("？") || $0.contains("?") }) {
        return question
    }
    return candidates.first ?? ""
}

func movementKey(_ texts: [TextItem]) -> String {
    let ignoredExact = Set([
        "test back", "答题", "背题", "question setting", "题目解析", "试题详解",
        "点击或上拉加载更多", "全部考点总结", "反馈", "查看解析"
    ])
    let parts = texts.map { clean($0.text) }.filter { text in
        !text.isEmpty
            && !ignoredExact.contains(text)
            && !text.hasPrefix("相关考点")
            && !text.hasPrefix("考友互动")
            && !text.hasPrefix("驾校一点通")
            && !text.hasPrefix("板书讲题")
            && !text.contains("IP属地")
    }
    return parts.prefix(18).joined(separator: "|")
}

func answerY(_ node: Node) -> Double? {
    let texts = [node.description, node.title, node.value].compactMap { $0?.trimmingCharacters(in: .whitespacesAndNewlines) }
    if texts.contains(where: { clean($0).hasPrefix("答案 ") }) {
        return node.position?.dropFirst().first
    }
    return node.children.compactMap(answerY).min()
}

func questionHasImageCandidate(_ node: Node, before answerTop: Double) -> Bool {
    let hasLargeUntitledButton =
        node.role == "AXButton"
        && (node.description ?? "").isEmpty
        && (node.title ?? "").isEmpty
        && (node.value ?? "").isEmpty
        && ((node.size?.first ?? 0) > 120)
        && ((node.size?.dropFirst().first ?? 0) > 80)
        && ((node.position?.dropFirst().first ?? Double.greatestFiniteMagnitude) < answerTop)
    return hasLargeUntitledButton || node.children.contains { questionHasImageCandidate($0, before: answerTop) }
}

func questionHasImageCandidate(_ node: Node) -> Bool {
    guard let answerTop = answerY(node) else { return false }
    return questionHasImageCandidate(node, before: answerTop)
}

func mouse(_ type: CGEventType, _ point: CGPoint) {
    CGEvent(mouseEventSource: nil, mouseType: type, mouseCursorPosition: point, mouseButton: .left)?.post(tap: .cghidEventTap)
}

func dragLeft(root: Node) {
    let winX = root.position?.first ?? 556
    let winY = root.position?.dropFirst().first ?? -999
    let y = winY + (questionHasImageCandidate(root) ? 650 : 330)
    let start = CGPoint(x: winX + 520, y: y)
    let end = CGPoint(x: winX + 120, y: y)
    mouse(.leftMouseDown, start)
    for step in 1...14 {
        let t = Double(step) / 14.0
        let p = CGPoint(x: start.x + (end.x - start.x) * t, y: start.y)
        mouse(.leftMouseDragged, p)
        usleep(12_000)
    }
    mouse(.leftMouseUp, end)
    usleep(750_000)
}

func capture(pid: pid_t, paper: Int, index: Int) -> (Record, Node) {
    let root = windowRoot(pid: pid)
    var texts: [TextItem] = []
    flattenTexts(root, &texts)
    let record = Record(
        paper: paper,
        index: index,
        questionKey: questionKey(texts),
        hasImageCandidate: questionHasImageCandidate(root),
        texts: texts
    )
    return (record, root)
}

guard CommandLine.arguments.count >= 5,
      let pid = Int32(CommandLine.arguments[1]),
      let paper = Int(CommandLine.arguments[2]),
      let count = Int(CommandLine.arguments[3]) else {
    fputs("Usage: scrape_current_paper.swift <pid> <paper> <count> <output-jsonl>\n", stderr)
    exit(2)
}

let outputPath = CommandLine.arguments[4]
if FileManager.default.fileExists(atPath: outputPath) {
    try FileManager.default.removeItem(atPath: outputPath)
}
FileManager.default.createFile(atPath: outputPath, contents: nil)
let outputURL = URL(fileURLWithPath: outputPath)
let handle = try FileHandle(forWritingTo: outputURL)
defer { try? handle.close() }

let encoder = JSONEncoder()
encoder.outputFormatting = [.sortedKeys]

for index in 1...count {
    let (record, root) = capture(pid: pid, paper: paper, index: index)
    let data = try encoder.encode(record)
    handle.write(data)
    handle.write("\n".data(using: .utf8)!)
    try handle.synchronize()
    fputs("paper \(paper) question \(index)/\(count): \(record.questionKey)\n", stderr)
    if index < count {
        var before = movementKey(record.texts)
        var moved = false
        for _ in 0..<3 {
            dragLeft(root: root)
            let (nextRecord, _) = capture(pid: pid, paper: paper, index: index + 1)
            let after = movementKey(nextRecord.texts)
            if !nextRecord.questionKey.isEmpty && after != before {
                moved = true
                break
            }
            before = after
        }
        if !moved {
            fputs("Warning: question did not visibly change after swipes at paper \(paper), index \(index)\n", stderr)
        }
    }
}
