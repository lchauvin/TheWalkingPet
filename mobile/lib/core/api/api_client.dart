import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

// Configure at build time via --dart-define=API_URL=https://...
// TODO: Switch to HTTPS in production.
const apiBaseUrl = String.fromEnvironment(
  'API_URL',
  defaultValue: 'http://192.168.2.21:8010/api/v1',
);
const _storageBase = String.fromEnvironment(
  'STORAGE_URL',
  defaultValue: 'http://192.168.2.21:8010/storage',
);

/// Convert a stored image path to a full URL.
/// Stored paths look like: storage\images\pets\{id}\file.jpg  (Windows)
/// Served at: /storage/pets/{id}/file.jpg
String imageUrl(String path) {
  // Normalize all backslashes and double-backslashes to forward slashes
  final normalized = path.replaceAll('\\\\', '/').replaceAll('\\', '/');
  // Strip leading "storage/images" prefix
  final relative = normalized
      .replaceFirst(RegExp(r'^storage/images/?'), '')
      .replaceFirst(RegExp(r'^/'), '');
  return '$_storageBase/$relative';
}

class ApiClient {
  static final ApiClient _instance = ApiClient._internal();
  factory ApiClient() => _instance;

  late final Dio _dio;
  final _storage = const FlutterSecureStorage();

  /// Called when a session expires and the refresh token is invalid.
  /// Set by AuthNotifier to redirect to login.
  void Function()? onSessionExpired;

  ApiClient._internal() {
    _dio = Dio(BaseOptions(
      baseUrl: apiBaseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
      sendTimeout: const Duration(seconds: 30),
    ));

    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await _storage.read(key: 'access_token');
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        handler.next(options);
      },
      onError: (error, handler) async {
        if (error.response?.statusCode == 401) {
          final refreshed = await _tryRefresh();
          if (refreshed) {
            // Retry original request with new token
            final token = await _storage.read(key: 'access_token');
            error.requestOptions.headers['Authorization'] = 'Bearer $token';
            final response = await _dio.fetch(error.requestOptions);
            handler.resolve(response);
            return;
          }
        }
        handler.next(error);
      },
    ));
  }

  Future<bool> _tryRefresh() async {
    try {
      final refreshToken = await _storage.read(key: 'refresh_token');
      if (refreshToken == null) return false;

      final response = await Dio().post(
        '$apiBaseUrl/auth/refresh',
        data: {'refresh_token': refreshToken},
      );
      await saveTokens(
        response.data['access_token'],
        response.data['refresh_token'],
      );
      return true;
    } catch (_) {
      await clearTokens();
      onSessionExpired?.call();
      return false;
    }
  }

  Future<void> saveTokens(String accessToken, String refreshToken) async {
    await _storage.write(key: 'access_token', value: accessToken);
    await _storage.write(key: 'refresh_token', value: refreshToken);
  }

  Future<void> clearTokens() async {
    await _storage.delete(key: 'access_token');
    await _storage.delete(key: 'refresh_token');
  }

  Future<bool> hasToken() async {
    final token = await _storage.read(key: 'access_token');
    return token != null;
  }

  Dio get dio => _dio;
}
