// F-4: rasterise page 1 of a PDF with Quartz (CoreGraphics), as Preview does,
// onto white at a given dpi.   swift quartz_render.swift IN.pdf OUT.png DPI
import Foundation
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers

let a = CommandLine.arguments
let doc = CGPDFDocument(URL(fileURLWithPath: a[1]) as CFURL)!
let page = doc.page(at: 1)!
let box = page.getBoxRect(.mediaBox)
let s = Double(a[3])! / 72.0
let w = Int((box.width * s).rounded()), h = Int((box.height * s).rounded())
let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0,
                    space: CGColorSpace(name: CGColorSpace.sRGB)!,
                    bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
ctx.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: 1))
ctx.fill(CGRect(x: 0, y: 0, width: w, height: h))
ctx.scaleBy(x: CGFloat(Double(w) / box.width), y: CGFloat(Double(h) / box.height))
ctx.drawPDFPage(page)
let img = ctx.makeImage()!
let dst = CGImageDestinationCreateWithURL(URL(fileURLWithPath: a[2]) as CFURL, UTType.png.identifier as CFString, 1, nil)!
CGImageDestinationAddImage(dst, img, nil)
CGImageDestinationFinalize(dst)
