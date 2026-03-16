import 'dart:io';
import 'package:dio/dio.dart';
import 'api_client.dart';
import '../../features/pets/models/pet.dart';

class PetsApi {
  final _client = ApiClient();

  Future<List<Pet>> getPets() async {
    final response = await _client.dio.get('/pets');
    return (response.data as List)
        .map((e) => Pet.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<Pet> createPet({
    required String name,
    required String species,
    String? breed,
    String? description,
    bool isMicrochipped = false,
  }) async {
    final response = await _client.dio.post('/pets', data: {
      'name': name,
      'species': species,
      if (breed != null && breed.isNotEmpty) 'breed': breed,
      if (description != null && description.isNotEmpty) 'description': description,
      'is_microchipped': isMicrochipped,
    });
    return Pet.fromJson(response.data as Map<String, dynamic>);
  }

  Future<Pet> uploadImage(String petId, File imageFile, {bool isPrimary = false}) async {
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(
        imageFile.path,
        filename: imageFile.path.split('/').last,
      ),
      'is_primary': isPrimary.toString(),
    });
    final response = await _client.dio.post(
      '/pets/$petId/images',
      data: formData,
    );
    // Refresh pet to get updated images
    return getPet(petId);
  }

  Future<Pet> getPet(String petId) async {
    final response = await _client.dio.get('/pets/$petId');
    return Pet.fromJson(response.data as Map<String, dynamic>);
  }

  Future<void> deletePet(String petId) async {
    await _client.dio.delete('/pets/$petId');
  }

  Future<void> deletePetImage(String petId, String imageId) async {
    await _client.dio.delete('/pets/$petId/images/$imageId');
  }
}
