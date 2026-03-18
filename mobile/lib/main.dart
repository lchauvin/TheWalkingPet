import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'core/notifications/fcm_service.dart';
import 'features/auth/providers/auth_provider.dart';
import 'features/auth/screens/login_screen.dart';
import 'features/auth/screens/register_screen.dart';
import 'features/lost/providers/lost_provider.dart';
import 'features/lost/screens/declare_lost_screen.dart';
import 'features/lost/screens/lost_declarations_screen.dart';
import 'features/matches/providers/matches_provider.dart';
import 'features/matches/screens/matches_screen.dart';
import 'features/pets/providers/pets_provider.dart';
import 'features/sightings/screens/submit_sighting_screen.dart';
import 'features/pets/screens/add_pet_screen.dart';
import 'features/pets/screens/pet_detail_screen.dart';
import 'features/pets/screens/pets_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();

  // Keep more decoded images in RAM so tab switches and scrolls are instant.
  PaintingBinding.instance.imageCache.maximumSize = 200;
  PaintingBinding.instance.imageCache.maximumSizeBytes = 150 << 20; // 150 MB

  runApp(const ProviderScope(child: TheWalkingPetApp()));
}

/// Bridges Riverpod auth state changes to GoRouter's refreshListenable.
class _AuthRefreshNotifier extends ChangeNotifier {
  void notify() => notifyListeners();
}

class TheWalkingPetApp extends ConsumerStatefulWidget {
  const TheWalkingPetApp({super.key});

  @override
  ConsumerState<TheWalkingPetApp> createState() => _TheWalkingPetAppState();
}

class _TheWalkingPetAppState extends ConsumerState<TheWalkingPetApp> {
  late final GoRouter _router;
  final _routerRefresh = _AuthRefreshNotifier();

  @override
  void initState() {
    super.initState();
    _router = GoRouter(
      refreshListenable: _routerRefresh,
      redirect: (context, state) {
        final authState = ref.read(authProvider);
        if (authState.status == AuthStatus.unknown) return null;
        final isAuth = authState.status == AuthStatus.authenticated;
        final isOnAuth = state.matchedLocation == '/login' ||
            state.matchedLocation == '/register';
        if (!isAuth && !isOnAuth) return '/login';
        if (isAuth && isOnAuth) return '/home';
        return null;
      },
      routes: [
        GoRoute(path: '/login', builder: (_, _) => const LoginScreen()),
        GoRoute(path: '/register', builder: (_, _) => const RegisterScreen()),
        ShellRoute(
          builder: (context, state, child) => MainShell(child: child),
          routes: [
            GoRoute(path: '/home', builder: (_, _) => const PetsScreen()),
            GoRoute(path: '/lost', builder: (_, _) => const LostDeclarationsScreen()),
            GoRoute(path: '/sightings', builder: (_, _) => const SubmitSightingScreen()),
            GoRoute(path: '/matches', builder: (_, _) => const MatchesScreen()),
            GoRoute(path: '/pets/add', builder: (_, _) => const AddPetScreen()),
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
  }

  @override
  void dispose() {
    _routerRefresh.dispose();
    _router.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    ref.listen(authProvider, (_, _) => _routerRefresh.notify());

    return MaterialApp.router(
      title: 'TheWalkingPet',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepOrange),
        useMaterial3: true,
      ),
      routerConfig: _router,
    );
  }
}

// The 4 tab screens are constant — created once and kept alive forever.
const _tabScreens = [
  PetsScreen(),
  LostDeclarationsScreen(),
  SubmitSightingScreen(),
  MatchesScreen(),
];

const _tabPaths = ['/home', '/lost', '/sightings', '/matches'];

class MainShell extends ConsumerStatefulWidget {
  final Widget child;
  const MainShell({super.key, required this.child});

  @override
  ConsumerState<MainShell> createState() => _MainShellState();
}

class _MainShellState extends ConsumerState<MainShell>
    with WidgetsBindingObserver {
  bool _fcmInitialized = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      ref.read(petsProvider.notifier).load();
      ref.read(lostProvider.notifier).load();
      ref.read(matchesProvider.notifier).load();
    }
  }

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

    // Determine which tab is "active" for the nav bar highlight.
    // Sub-routes under /pets (detail, add, declare-lost) keep "My Pets" highlighted.
    final navIndex = location.startsWith('/lost')
        ? 1
        : location.startsWith('/sightings')
            ? 2
            : location.startsWith('/matches')
                ? 3
                : 0;

    // Main tab routes use IndexedStack so screens are never disposed.
    // Sub-routes (/pets/:id, /pets/add, etc.) render via widget.child as usual.
    final isMainTab = _tabPaths.contains(location);

    final matchesAsync = ref.watch(matchesProvider);
    final pendingCount =
        matchesAsync.valueOrNull?.where((m) => m.isPending).length ?? 0;

    return Scaffold(
      body: isMainTab
          ? IndexedStack(index: navIndex, children: _tabScreens)
          : widget.child,
      bottomNavigationBar: NavigationBar(
        selectedIndex: navIndex,
        onDestinationSelected: (i) => context.go(_tabPaths[i]),
        destinations: [
          const NavigationDestination(icon: Icon(Icons.pets), label: 'My Pets'),
          const NavigationDestination(icon: Icon(Icons.search), label: 'Lost'),
          const NavigationDestination(
              icon: Icon(Icons.camera_alt), label: 'Sighting'),
          NavigationDestination(
            icon: pendingCount > 0
                ? Badge.count(
                    count: pendingCount,
                    child: const Icon(Icons.notifications_outlined),
                  )
                : const Icon(Icons.notifications_outlined),
            label: 'Matches',
          ),
        ],
      ),
    );
  }
}
