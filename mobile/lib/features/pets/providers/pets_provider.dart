import 'dart:io';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/api/pets_api.dart';
import '../models/pet.dart';

class PetsNotifier extends StateNotifier<AsyncValue<List<Pet>>> {
  final _api = PetsApi();

  PetsNotifier() : super(const AsyncValue.loading()) {
    load();
  }

  Future<void> load() async {
    state = const AsyncValue.loading();
    try {
      final pets = await _api.getPets();
      state = AsyncValue.data(pets);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<Pet?> createPet({
    required String name,
    required String species,
    String? breed,
    String? description,
    bool isMicrochipped = false,
  }) async {
    try {
      final pet = await _api.createPet(
        name: name,
        species: species,
        breed: breed,
        description: description,
        isMicrochipped: isMicrochipped,
      );
      state = state.whenData((pets) => [...pets, pet]);
      return pet;
    } catch (_) {
      return null;
    }
  }

  Future<void> uploadImage(String petId, File imageFile, {bool isPrimary = false}) async {
    try {
      final updated = await _api.uploadImage(petId, imageFile, isPrimary: isPrimary);
      state = state.whenData(
        (pets) => pets.map((p) => p.id == petId ? updated : p).toList(),
      );
    } catch (_) {
      rethrow;
    }
  }

  Future<void> deletePet(String petId) async {
    try {
      await _api.deletePet(petId);
      state = state.whenData((pets) => pets.where((p) => p.id != petId).toList());
    } catch (_) {
      rethrow;
    }
  }

  Future<void> deletePetImage(String petId, String imageId) async {
    try {
      await _api.deletePetImage(petId, imageId);
      state = state.whenData((pets) => pets.map((p) {
        if (p.id != petId) return p;
        final updatedImages = p.images.where((i) => i.id != imageId).toList();
        return Pet(
          id: p.id,
          name: p.name,
          species: p.species,
          breed: p.breed,
          description: p.description,
          isMicrochipped: p.isMicrochipped,
          images: updatedImages,
        );
      }).toList());
    } catch (_) {
      rethrow;
    }
  }
}

final petsProvider = StateNotifierProvider<PetsNotifier, AsyncValue<List<Pet>>>(
  (_) => PetsNotifier(),
);
