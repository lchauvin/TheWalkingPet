import 'api_client.dart';

class AuthApi {
  final _client = ApiClient();

  Future<Map<String, dynamic>> register({
    required String email,
    required String password,
    String? displayName,
  }) async {
    final response = await _client.dio.post('/auth/register', data: {
      'email': email,
      'password': password,
      if (displayName != null && displayName.isNotEmpty) 'display_name': displayName,
    });
    return response.data as Map<String, dynamic>;
  }

  Future<void> login({
    required String email,
    required String password,
  }) async {
    final response = await _client.dio.post('/auth/login', data: {
      'email': email,
      'password': password,
    });
    await _client.saveTokens(
      response.data['access_token'],
      response.data['refresh_token'],
    );
  }

  /// Revokes the refresh token server-side, then clears local state.
  /// Local tokens are dropped even if the call fails — a logout must never
  /// leave credentials on the device.
  Future<void> logout() async {
    try {
      final refreshToken = await _client.readRefreshToken();
      await _client.dio.post(
        '/auth/logout',
        data: {'refresh_token': refreshToken},
      );
    } finally {
      await _client.clearTokens();
    }
  }
}
