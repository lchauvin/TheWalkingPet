import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/api/matches_api.dart';
import '../models/match.dart';

class MatchesNotifier extends StateNotifier<AsyncValue<List<PetMatch>>> {
  final _api = MatchesApi();

  MatchesNotifier() : super(const AsyncValue.loading()) {
    load();
  }

  Future<void> load() async {
    state = const AsyncValue.loading();
    try {
      final matches = await _api.getMatches();
      state = AsyncValue.data(matches);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<PetMatch?> confirm(String matchId) async {
    try {
      final updated = await _api.confirm(matchId);
      _updateMatch(updated);
      return updated;
    } catch (_) {
      return null;
    }
  }

  Future<void> reject(String matchId) async {
    try {
      final updated = await _api.reject(matchId);
      _updateMatch(updated);
    } catch (_) {
      rethrow;
    }
  }

  void _updateMatch(PetMatch updated) {
    state = state.whenData(
      (list) => list.map((m) => m.id == updated.id ? updated : m).toList(),
    );
  }
}

final matchesProvider =
    StateNotifierProvider<MatchesNotifier, AsyncValue<List<PetMatch>>>(
  (_) => MatchesNotifier(),
);
