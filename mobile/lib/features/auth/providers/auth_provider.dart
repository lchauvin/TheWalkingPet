import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/api/api_client.dart';
import '../../../core/api/auth_api.dart';
import '../../../core/api/google_auth.dart';

enum AuthStatus { unknown, authenticated, unauthenticated }

class AuthState {
  final AuthStatus status;
  final String? error;

  const AuthState({this.status = AuthStatus.unknown, this.error});

  AuthState copyWith({AuthStatus? status, String? error}) =>
      AuthState(status: status ?? this.status, error: error);
}

class AuthNotifier extends StateNotifier<AuthState> {
  final _api = AuthApi();
  final _client = ApiClient();

  AuthNotifier() : super(const AuthState()) {
    _checkAuth();
  }

  Future<void> _checkAuth() async {
    final has = await _client.hasToken();
    state = AuthState(status: has ? AuthStatus.authenticated : AuthStatus.unauthenticated);
  }

  Future<void> login(String email, String password) async {
    state = state.copyWith(error: null);
    try {
      await _api.login(email: email, password: password);
      state = const AuthState(status: AuthStatus.authenticated);
    } on DioException catch (e) {
      state = state.copyWith(
        status: AuthStatus.unauthenticated,
        error: _parseError(e),
      );
    }
  }

  Future<bool> register(String email, String password, String? displayName) async {
    state = state.copyWith(error: null);
    try {
      await _api.register(email: email, password: password, displayName: displayName);
      return true;
    } on DioException catch (e) {
      state = state.copyWith(error: _parseError(e));
      return false;
    }
  }

  Future<void> googleLogin() async {
    state = state.copyWith(error: null);
    try {
      await GoogleAuthService.signIn();
      state = const AuthState(status: AuthStatus.authenticated);
    } catch (e) {
      // ignore: avoid_print
      print('[GoogleLogin] error: $e');
      String message;
      if (e is DioException) {
        message = _parseError(e);
      } else {
        final raw = e.toString();
        if (raw.contains('sign_in_cancelled') || raw.contains('12501')) {
          return; // User cancelled — no error to show
        } else if (raw.contains('network_error') || raw.contains('7')) {
          message = 'Network error. Check your connection and try again.';
        } else if (raw.contains('sign_in_failed') || raw.contains('ApiException')) {
          message = 'Google Sign In failed. Make sure your Google account is set up on this device.';
        } else {
          message = 'Google Sign In failed. Please try again.';
        }
      }
      state = state.copyWith(
        status: AuthStatus.unauthenticated,
        error: message,
      );
    }
  }

  Future<void> logout() async {
    await GoogleAuthService.signOut();
    await _api.logout();
    state = const AuthState(status: AuthStatus.unauthenticated);
  }

  String _parseError(DioException e) {
    final detail = e.response?.data?['detail'];
    if (detail is String) return detail;
    return 'An error occurred. Please try again.';
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>(
  (_) => AuthNotifier(),
);
