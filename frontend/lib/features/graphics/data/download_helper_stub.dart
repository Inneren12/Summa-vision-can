import 'dart:io';
import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:path_provider/path_provider.dart';

/// Downloads [imageUrl] and saves it to the user's Downloads or Documents folder.
Future<String> downloadAndSaveImage(String imageUrl) async {
  final dio = Dio();
  final response = await dio.get<List<int>>(
    imageUrl,
    options: Options(responseType: ResponseType.bytes),
  );
  final bytes = Uint8List.fromList(response.data!);

  final dir =
      await getDownloadsDirectory() ?? await getApplicationDocumentsDirectory();
  final filename = 'summa_vision_${DateTime.now().millisecondsSinceEpoch}.png';
  final file = File('${dir.path}/$filename');
  await file.writeAsBytes(bytes);

  return file.path;
}
