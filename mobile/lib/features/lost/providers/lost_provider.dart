import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/api/lost_api.dart';
import '../models/lost_declaration.dart';

class LostNotifier extends StateNotifier<AsyncValue<List<LostDeclaration>>> {
  final _api = LostApi();

  LostNotifier() : super(const AsyncValue.loading()) {
    load();
  }

  Future<void> load() async {
    state = const AsyncValue.loading();
    try {
      final declarations = await _api.getMyDeclarations();
      state = AsyncValue.data(declarations);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<LostDeclaration?> declare({
    required String petId,
    required double lat,
    required double lon,
    String? description,
    double? rewardAmount,
  }) async {
    try {
      final decl = await _api.declare(
        petId: petId,
        lat: lat,
        lon: lon,
        description: description,
        rewardAmount: rewardAmount,
      );
      state = state.whenData((list) => [decl, ...list]);
      return decl;
    } catch (_) {
      return null;
    }
  }

  Future<void> markFound(String declarationId) async {
    try {
      final updated = await _api.updateStatus(declarationId, 'FOUND');
      state = state.whenData(
        (list) => list.map((d) => d.id == declarationId ? updated : d).toList(),
      );
    } catch (_) {
      rethrow;
    }
  }

  Future<void> cancel(String declarationId) async {
    try {
      final updated = await _api.updateStatus(declarationId, 'CANCELLED');
      state = state.whenData(
        (list) => list.map((d) => d.id == declarationId ? updated : d).toList(),
      );
    } catch (_) {
      rethrow;
    }
  }
}

final lostProvider =
    StateNotifierProvider<LostNotifier, AsyncValue<List<LostDeclaration>>>(
  (_) => LostNotifier(),
);
