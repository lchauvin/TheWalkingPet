import 'api_client.dart';
import '../../features/matches/models/match.dart';

class MatchesApi {
  final _client = ApiClient();

  Future<List<PetMatch>> getMatches({String? status}) async {
    final response = await _client.dio.get(
      '/matches',
      queryParameters: status != null ? {'status': status} : null,
    );
    return (response.data as List)
        .map((e) => PetMatch.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<PetMatch> confirm(String matchId) async {
    final response = await _client.dio.post('/matches/$matchId/confirm');
    return PetMatch.fromJson(response.data as Map<String, dynamic>);
  }

  Future<PetMatch> reject(String matchId) async {
    final response = await _client.dio.post('/matches/$matchId/reject');
    return PetMatch.fromJson(response.data as Map<String, dynamic>);
  }
}
