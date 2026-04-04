// ignore: avoid_web_libraries_in_flutter
import 'dart:html' as html;

/// Triggers a browser download of [imageUrl] via AnchorElement.
Future<String> downloadAndSaveImage(String imageUrl) async {
  final anchor = html.AnchorElement(href: imageUrl)
    ..setAttribute('download', 'summa_vision.png')
    ..style.display = 'none';
  html.document.body?.append(anchor);
  anchor.click();
  anchor.remove();
  return 'downloaded via browser';
}
