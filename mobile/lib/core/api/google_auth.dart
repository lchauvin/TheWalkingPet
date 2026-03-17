import 'package:google_sign_in/google_sign_in.dart';
import 'api_client.dart';

class GoogleAuthService {
  static final _googleSignIn = GoogleSignIn(
    scopes: ['email', 'profile'],
    serverClientId: '1068737121409-vp31cm0csustcvntkvpqvae1thra50oa.apps.googleusercontent.com',
  );

  static Future<void> signIn() async {
    final account = await _googleSignIn.signIn();
    if (account == null) throw Exception('Google sign in cancelled');

    final auth = await account.authentication;
    final idToken = auth.idToken;
    if (idToken == null) throw Exception('Failed to get ID token');

    final response = await ApiClient().dio.post(
      '/auth/google',
      data: {'id_token': idToken},
    );

    await ApiClient().saveTokens(
      response.data['access_token'],
      response.data['refresh_token'],
    );
  }

  static Future<void> signOut() async {
    await _googleSignIn.signOut();
    await ApiClient().clearTokens();
  }
}
