import ApplicationServices
import Foundation

guard CommandLine.arguments.count >= 2,
      let pid = Int32(CommandLine.arguments[1]) else {
    fputs("Usage: window_id.swift <pid>\n", stderr)
    exit(2)
}

let windowInfo = (CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]]) ?? []
let matches = windowInfo.filter { info in
    (info[kCGWindowOwnerPID as String] as? Int32) == pid
        && ((info[kCGWindowLayer as String] as? Int) ?? 999) == 0
}

for info in matches {
    let id = info[kCGWindowNumber as String] ?? ""
    let name = info[kCGWindowName as String] ?? ""
    let owner = info[kCGWindowOwnerName as String] ?? ""
    let bounds = info[kCGWindowBounds as String] ?? [:]
    print("\(id)\t\(owner)\t\(name)\t\(bounds)")
}
