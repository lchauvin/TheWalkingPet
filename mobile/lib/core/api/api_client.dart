import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../config/server_config.dart';

/// Full URL for a stored image path.
///
/// Images are served by an authenticated route, not a public static mount, so
/// every request needs [authImageHeaders]. Stored paths are relative and POSIX
/// (`pets/<id>/file.jpg`); the leading-prefix stripping below only exists for
/// rows written before migration 007 normalised them.
String imageUrl(String path) {
  final normalized = path.replaceAll('\\\\', '/').replaceAll('\\', '/');
  final relative = normalized
      .replaceFirst(RegExp(r'^\.?/?storage/images/?'), '')
      .replaceFirst(RegExp(r'^/'), '');
  return '${ServerConfig.apiBaseUrl}/media/$relative';
}

/// Authorization header for image requests. Empty when signed out, which makes
/// the image fail to load rather than silently render someone else's pet.
Map<String, String> authImageHeaders() {
  final token = ApiClient().cachedAccessToken;
  return token == null ? const {} : {'Authorization': 'Bearer $token'};
}

class ApiClient {
  static final ApiClient _instance = ApiClient._internal();
  factory ApiClient() => _instance;

  late final Dio _dio;
  final _storage = const FlutterSecureStorage();

  /// Mirrors the stored access token so image widgets can build a header
  /// synchronously. Kept in step by [saveTokens], [clearTokens] and [primeTokens].
  String? _accessToken;
  String? get cachedAccessToken => _accessToken;

  /// Called when a session expires and the refresh token is invalid.
  /// Set by AuthNotifier to redirect to login.
  void Function()? onSessionExpired;

  ApiClient._internal() {
    _dio = Dio(BaseOptions(
      baseUrl: ServerConfig.apiBaseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
      sendTimeout: const Duration(seconds: 30),
    ));

    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = _accessToken ?? await _storage.read(key: 'access_token');
        if (token != null) {
          _accessToken = token;
          options.headers['Authorization'] = 'Bearer $token';
        }
        handler.next(options);
      },
      onError: (error, handler) async {
        if (error.response?.statusCode == 401) {
          final refreshed = await _tryRefresh();
          if (refreshed) {
            // Retry original request with new token
            error.requestOptions.headers['Authorization'] = 'Bearer $_accessToken';
            try {
              final response = await _dio.fetch(error.requestOptions);
              handler.resolve(response);
            } on DioException catch (e) {
              handler.next(e);
            }
            return;
          }
        }
        handler.next(error);
      },
    ));
  }

  /// Loads the stored access token into memory. Await before first paint so
  /// image widgets have a header on their very first build.
  Future<void> primeTokens() async {
    _accessToken = await _storage.read(key: 'access_token');
  }

  /// Called after the server address changes in Settings so in-flight
  /// requests and future ones target the new host.
  void updateBaseUrl() {
    _dio.options.baseUrl = ServerConfig.apiBaseUrl;
  }

  Future<bool> _tryRefresh() async {
    try {
      final refreshToken = await _storage.read(key: 'refresh_token');
      if (refreshToken == null) return false;

      // A bare Dio instance: this must not recurse through the 401 interceptor.
      final response = await Dio().post(
        '${ServerConfig.apiBaseUrl}/auth/refresh',
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
    _accessToken = accessToken;
    await _storage.write(key: 'access_token', value: accessToken);
    await _storage.write(key: 'refresh_token', value: refreshToken);
  }

  Future<String?> readRefreshToken() => _storage.read(key: 'refresh_token');

  Future<void> clearTokens() async {
    _accessToken = null;
    await _storage.delete(key: 'access_token');
    await _storage.delete(key: 'refresh_token');
  }

  Future<bool> hasToken() async {
    final token = _accessToken ?? await _storage.read(key: 'access_token');
    return token != null;
  }

  Dio get dio => _dio;
}
