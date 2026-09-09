import 'dart:io';
import 'package:dio/dio.dart';
import 'api_client.dart';
import '../location/location_resolution.dart';
import '../../features/sightings/models/sighting.dart';

class SightingsApi {
  final _client = ApiClient();

  Future<Sighting> submit({
    required File image,
    required double latitude,
    required double longitude,
    required LocationSource source,
    DateTime? takenAt,
  }) async {
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(
        image.path,
        filename: image.path.split('/').last,
      ),
      'latitude': latitude.toString(),
      'longitude': longitude.toString(),
      'location_source': source.wireValue,
      if (takenAt != null)
        'taken_at': takenAt.toUtc().toIso8601String(),
    });

    final response = await _client.dio.post('/sightings', data: formData);
    return Sighting.fromJson(response.data as Map<String, dynamic>);
  }
}
