import 'dart:io';
import 'package:dio/dio.dart';
import 'api_client.dart';
import '../../features/sightings/models/sighting.dart';

class SightingsApi {
  final _client = ApiClient();

  Future<Sighting> submit({
    required File image,
    required double latitude,
    required double longitude,
  }) async {
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(
        image.path,
        filename: image.path.split('/').last,
      ),
      'latitude': latitude.toString(),
      'longitude': longitude.toString(),
    });

    final response = await _client.dio.post('/sightings', data: formData);
    return Sighting.fromJson(response.data as Map<String, dynamic>);
  }
}
