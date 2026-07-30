import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Backend server address, configurable at runtime from Settings.
///
/// Defaults to the build-time value (--dart-define=API_HOST=http://host:port)
/// but can be overridden and persisted on-device — useful when the backend's
/// IP changes, e.g. when reached over Tailscale.
class ServerConfig {
  static const defaultHost = String.fromEnvironment(
    'API_HOST',
    defaultValue: 'http://192.168.2.21:8010',
  );

  static const _key = 'server_host';
  static const _storage = FlutterSecureStorage();

  static String _host = defaultHost;

  static String get host => _host;
  static String get apiBaseUrl => '$_host/api/v1';
  static String get storageBaseUrl => '$_host/storage';

  /// Loads the persisted host override, if any. Must be awaited before
  /// [ApiClient] is first constructed (i.e. before `runApp`).
  static Future<void> init() async {
    final saved = await _storage.read(key: _key);
    if (saved != null && saved.isNotEmpty) {
      _host = saved;
    }
  }

  /// Normalizes and persists [input] as the new server host.
  /// Accepts forms like "100.101.102.103:8010" or "http://host:8010/".
  static Future<void> setHost(String input) async {
    _host = _normalize(input);
    await _storage.write(key: _key, value: _host);
  }

  static Future<void> resetToDefault() async {
    _host = defaultHost;
    await _storage.delete(key: _key);
  }

  static String _normalize(String input) {
    var h = input.trim();
    while (h.endsWith('/')) {
      h = h.substring(0, h.length - 1);
    }
    if (!h.startsWith('http://') && !h.startsWith('https://')) {
      h = 'http://$h';
    }
    return h;
  }
}
