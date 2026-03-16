import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'core/notifications/fcm_service.dart';
import 'features/auth/providers/auth_provider.dart';
import 'features/auth/screens/login_screen.dart';
import 'features/auth/screens/register_screen.dart';
import 'features/lost/screens/declare_lost_screen.dart';
import 'features/lost/screens/lost_declarations_screen.dart';
import 'features/matches/screens/matches_screen.dart';
import 'features/sightings/screens/submit_sighting_screen.dart';
import 'features/pets/screens/add_pet_screen.dart';
import 'features/pets/screens/pet_detail_screen.dart';
import 'features/pets/screens/pets_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
  runApp(const ProviderScope(child: TheWalkingPetApp()));
}

class TheWalkingPetApp extends ConsumerWidget {
  const TheWalkingPetApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);

    final router = GoRouter(
      redirect: (context, state) {
        if (authState.status == AuthStatus.unknown) return null;
        final isAuth = authState.status == AuthStatus.authenticated;
        final isOnAuth = state.matchedLocation == '/login' ||
            state.matchedLocation == '/register';
        if (!isAuth && !isOnAuth) return '/login';
        if (isAuth && isOnAuth) return '/home';
        return null;
      },
      routes: [
        GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
        GoRoute(path: '/register', builder: (_, __) => const RegisterScreen()),
        ShellRoute(
          builder: (context, state, child) => MainShell(child: child),
          routes: [
            GoRoute(path: '/home', builder: (_, __) => const PetsScreen()),
            GoRoute(path: '/lost', builder: (_, __) => const LostDeclarationsScreen()),
            GoRoute(path: '/sightings', builder: (_, __) => const SubmitSightingScreen()),
            GoRoute(path: '/matches', builder: (_, __) => const MatchesScreen()),
            GoRoute(path: '/pets/add', builder: (_, __) => const AddPetScreen()),
            GoRoute(
              path: '/pets/:id',
              builder: (_, state) =>
                  PetDetailScreen(petId: state.pathParameters['id']!),
            ),
            GoRoute(
              path: '/pets/:id/declare-lost',
              builder: (_, state) => DeclareLostScreen(
                petId: state.pathParameters['id']!,
                petName: state.extra as String? ?? 'Pet',
              ),
            ),
          ],
        ),
      ],
      initialLocation: '/login',
    );

    return MaterialApp.router(
      title: 'TheWalkingPet',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepOrange),
        useMaterial3: true,
      ),
      routerConfig: router,
    );
  }
}

class MainShell extends ConsumerStatefulWidget {
  final Widget child;
  const MainShell({super.key, required this.child});

  @override
  ConsumerState<MainShell> createState() => _MainShellState();
}

class _MainShellState extends ConsumerState<MainShell> {
  bool _fcmInitialized = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_fcmInitialized) {
      _fcmInitialized = true;
      FcmService.init(context, ref);
    }
  }

  @override
  Widget build(BuildContext context) {
    final location = GoRouterState.of(context).matchedLocation;
    final index = location.startsWith('/lost')
        ? 1
        : location.startsWith('/sightings')
            ? 2
            : location.startsWith('/matches')
                ? 3
                : 0;

    return Scaffold(
      body: widget.child,
      bottomNavigationBar: NavigationBar(
        selectedIndex: index,
        onDestinationSelected: (i) {
          if (i == 0) context.go('/home');
          if (i == 1) context.go('/lost');
          if (i == 2) context.go('/sightings');
          if (i == 3) context.go('/matches');
        },
        destinations: const [
          NavigationDestination(icon: Icon(Icons.pets), label: 'My Pets'),
          NavigationDestination(icon: Icon(Icons.search), label: 'Lost'),
          NavigationDestination(icon: Icon(Icons.camera_alt), label: 'Sighting'),
          NavigationDestination(icon: Icon(Icons.notifications_outlined), label: 'Matches'),
        ],
      ),
    );
  }
}
