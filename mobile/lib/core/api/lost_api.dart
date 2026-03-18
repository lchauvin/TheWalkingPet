import 'api_client.dart';
import '../../features/lost/models/lost_declaration.dart';

class LostApi {
  final _client = ApiClient();

  Future<List<LostDeclaration>> getMyDeclarations() async {
    final response = await _client.dio.get('/lost-declarations');
    return (response.data as List)
        .map((e) => LostDeclaration.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<LostDeclaration> declare({
    required String petId,
    required double lat,
    required double lon,
    String? description,
    double? rewardAmount,
  }) async {
    final response = await _client.dio.post('/lost-declarations', data: {
      'pet_id': petId,
      'last_seen_lat': lat,
      'last_seen_lon': lon,
      if (description != null && description.isNotEmpty) 'description': description,
      'reward_amount': ?rewardAmount,
    });
    return LostDeclaration.fromJson(response.data as Map<String, dynamic>);
  }

  Future<LostDeclaration> updateStatus(String declarationId, String status) async {
    final response = await _client.dio.put(
      '/lost-declarations/$declarationId',
      data: {'status': status},
    );
    return LostDeclaration.fromJson(response.data as Map<String, dynamic>);
  }
}
