import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../api/api_client.dart';
import '../../features/matches/providers/matches_provider.dart';

class FcmService {
  static final _messaging = FirebaseMessaging.instance;

  /// Request permission and register token with backend.
  static Future<void> init(BuildContext context, WidgetRef ref) async {
    final settings = await _messaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );

    if (settings.authorizationStatus != AuthorizationStatus.authorized) {
      return;
    }

    final token = await _messaging.getToken();
    if (token != null) {
      await _sendTokenToBackend(token);
    }

    // Re-register if token refreshes
    _messaging.onTokenRefresh.listen(_sendTokenToBackend);

    // Show notification when app is in foreground
    FirebaseMessaging.onMessage.listen((message) {
      final notification = message.notification;
      if (notification != null && context.mounted) {
        final messenger = ScaffoldMessenger.of(context);
        messenger.clearSnackBars();
        messenger.showSnackBar(
          SnackBar(
            content: Text('${notification.title}: ${notification.body}'),
            duration: const Duration(seconds: 6),
            backgroundColor: Colors.deepOrange,
            behavior: SnackBarBehavior.floating,
            showCloseIcon: true,
            closeIconColor: Colors.white,
            action: SnackBarAction(
              label: 'View',
              textColor: Colors.white,
              onPressed: () {
                ref.read(matchesProvider.notifier).load();
                context.go('/matches');
              },
            ),
          ),
        );
      }
    });

    // Navigate to matches when notification is tapped (app in background)
    FirebaseMessaging.onMessageOpenedApp.listen((message) {
      if (context.mounted) {
        ref.read(matchesProvider.notifier).load();
        context.go('/matches');
      }
    });
  }

  static Future<void> _sendTokenToBackend(String token) async {
    try {
      await ApiClient().dio.put('/auth/fcm-token', data: {'fcm_token': token});
    } catch (_) {}
  }
}
