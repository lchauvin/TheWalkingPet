import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../../core/api/api_client.dart';
import '../providers/matches_provider.dart';
import '../models/match.dart';
import '../../lost/providers/lost_provider.dart';
import '../../pets/providers/pets_provider.dart';

class MatchesScreen extends ConsumerStatefulWidget {
  const MatchesScreen({super.key});

  @override
  ConsumerState<MatchesScreen> createState() => _MatchesScreenState();
}

class _MatchesScreenState extends ConsumerState<MatchesScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(matchesProvider.notifier).load();
    });
  }

  @override
  Widget build(BuildContext context) {
    final matchesAsync = ref.watch(matchesProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Matches'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.read(matchesProvider.notifier).load(),
          ),
        ],
      ),
      body: matchesAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline, size: 48, color: Colors.red),
              const SizedBox(height: 8),
              const Text('Failed to load matches.'),
              TextButton(
                onPressed: () => ref.read(matchesProvider.notifier).load(),
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
        data: (matches) {
          if (matches.isEmpty) {
            return const Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.find_in_page_outlined, size: 64, color: Colors.grey),
                  SizedBox(height: 8),
                  Text('No matches yet', style: TextStyle(color: Colors.grey)),
                  SizedBox(height: 4),
                  Text(
                    'Matches appear here when a sighting\nclosely resembles one of your lost pets.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Colors.grey, fontSize: 12),
                  ),
                ],
              ),
            );
          }

          final pending = matches.where((m) => m.isPending).toList();
          final resolved = matches.where((m) => !m.isPending).toList();

          return RefreshIndicator(
            onRefresh: () => ref.read(matchesProvider.notifier).load(),
            child: ListView(
              padding: const EdgeInsets.all(12),
              children: [
                if (pending.isNotEmpty) ...[
                  _SectionHeader(
                      '${pending.length} Pending Match${pending.length > 1 ? 'es' : ''}'),
                  ...pending.map((m) => _MatchCard(match: m)),
                ],
                if (resolved.isNotEmpty) ...[
                  const _SectionHeader('Resolved'),
                  ...resolved.map((m) => _MatchCard(match: m)),
                ],
              ],
            ),
          );
        },
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final String title;
  const _SectionHeader(this.title);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Text(title,
          style: Theme.of(context)
              .textTheme
              .titleSmall
              ?.copyWith(color: Colors.grey)),
    );
  }
}

class _MatchCard extends ConsumerWidget {
  final PetMatch match;
  const _MatchCard({required this.match});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final petsAsync = ref.watch(petsProvider);
    final lostAsync = ref.watch(lostProvider);

    // Find pet name via declaration
    final declaration = lostAsync.valueOrNull
        ?.where((d) => d.id == match.lostDeclarationId)
        .firstOrNull;
    final pet = petsAsync.valueOrNull
        ?.where((p) => p.id == declaration?.petId)
        .firstOrNull;
    final petName = pet?.name ?? 'Unknown pet';

    final scorePercent = (match.similarityScore * 100).toStringAsFixed(1);
    final statusColor = match.isPending
        ? Colors.orange
        : match.isConfirmed
            ? Colors.green
            : Colors.grey;

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Sighting photo — tap to view full screen
            if (match.sightingImagePath != null)
              GestureDetector(
                onTap: () => _openFullScreen(context, match.sightingImagePath!),
                child: Hero(
                  tag: 'sighting_image_${match.id}',
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(8),
                    child: Stack(
                      alignment: Alignment.topRight,
                      children: [
                        CachedNetworkImage(
                          imageUrl: imageUrl(match.sightingImagePath!),
                          height: 180,
                          width: double.infinity,
                          fit: BoxFit.cover,
                          placeholder: (_, _) => Container(
                            height: 180,
                            color: Colors.grey.shade100,
                            child: const Center(
                              child: CircularProgressIndicator(),
                            ),
                          ),
                          errorWidget: (_, _, _) => Container(
                            height: 180,
                            color: Colors.grey.shade200,
                            child: const Icon(Icons.broken_image,
                                color: Colors.grey, size: 48),
                          ),
                        ),
                        Padding(
                          padding: const EdgeInsets.all(6),
                          child: Container(
                            decoration: BoxDecoration(
                              color: Colors.black45,
                              borderRadius: BorderRadius.circular(4),
                            ),
                            padding: const EdgeInsets.all(3),
                            child: const Icon(Icons.zoom_in,
                                color: Colors.white, size: 16),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            if (match.sightingImagePath != null) const SizedBox(height: 12),

            Row(
              children: [
                Expanded(
                  child: Text(petName,
                      style: const TextStyle(
                          fontWeight: FontWeight.bold, fontSize: 16)),
                ),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: statusColor.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: statusColor),
                  ),
                  child: Text(match.status,
                      style: TextStyle(color: statusColor, fontSize: 12)),
                ),
              ],
            ),
            const SizedBox(height: 8),

            // Similarity score bar
            Row(
              children: [
                const Text('Similarity: ',
                    style: TextStyle(color: Colors.grey)),
                Expanded(
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(4),
                    child: LinearProgressIndicator(
                      value: match.similarityScore,
                      minHeight: 8,
                      backgroundColor: Colors.grey.shade200,
                      valueColor: AlwaysStoppedAnimation(
                        match.similarityScore >= 0.85
                            ? Colors.green
                            : match.similarityScore >= 0.7
                                ? Colors.orange
                                : Colors.red,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Text('$scorePercent%',
                    style: const TextStyle(fontWeight: FontWeight.bold)),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              'Spotted on ${_formatDate(match.createdAt)}',
              style: const TextStyle(color: Colors.grey, fontSize: 12),
            ),

            // Confirmed: show GPS location
            if (match.isConfirmed &&
                match.sightingLat != null &&
                match.sightingLon != null) ...[
              const SizedBox(height: 10),
              GestureDetector(
                onTap: () async {
                  final uri = Uri.parse(
                    'https://www.google.com/maps/search/?api=1&query='
                    '${match.sightingLat},${match.sightingLon}',
                  );
                  await launchUrl(uri, mode: LaunchMode.externalApplication);
                },
                child: Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.green.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.green.shade300),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.location_on, color: Colors.green),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('Sighting location',
                                style: TextStyle(
                                    fontWeight: FontWeight.bold,
                                    color: Colors.green)),
                            Text(
                              '${match.sightingLat!.toStringAsFixed(5)}, '
                              '${match.sightingLon!.toStringAsFixed(5)}',
                              style: const TextStyle(
                                  color: Colors.green, fontSize: 12),
                            ),
                          ],
                        ),
                      ),
                      const Icon(Icons.open_in_new,
                          color: Colors.green, size: 16),
                    ],
                  ),
                ),
              ),
            ],

            // Pending: confirm / reject buttons
            if (match.isPending) ...[
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () => _reject(context, ref),
                      icon: const Icon(Icons.close, color: Colors.red),
                      label: const Text('Not my pet',
                          style: TextStyle(color: Colors.red)),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: () => _confirm(context, ref),
                      icon: const Icon(Icons.check),
                      label: const Text('That\'s my pet!'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.green,
                        foregroundColor: Colors.white,
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  void _openFullScreen(BuildContext context, String imagePath) {
    Navigator.of(context).push(
      PageRouteBuilder(
        opaque: false,
        barrierColor: Colors.black87,
        pageBuilder: (_, _, _) => _FullScreenImageViewer(
          imageUrl: imageUrl(imagePath),
          heroTag: 'sighting_image_${match.id}',
        ),
        transitionsBuilder: (_, animation, _, child) =>
            FadeTransition(opacity: animation, child: child),
      ),
    );
  }

  Future<void> _confirm(BuildContext context, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Confirm Match'),
        content: const Text(
            'Are you sure this is your pet? This will reveal the sighting location.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            style:
                ElevatedButton.styleFrom(backgroundColor: Colors.green),
            child: const Text('Yes, that\'s my pet!',
                style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      await ref.read(matchesProvider.notifier).confirm(match.id);
    }
  }

  Future<void> _reject(BuildContext context, WidgetRef ref) async {
    await ref.read(matchesProvider.notifier).reject(match.id);
  }

  String _formatDate(DateTime dt) {
    return '${dt.day}/${dt.month}/${dt.year} at ${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
  }
}

class _FullScreenImageViewer extends StatelessWidget {
  final String imageUrl;
  final String heroTag;

  const _FullScreenImageViewer({
    required this.imageUrl,
    required this.heroTag,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: Stack(
        children: [
          // Zoom/pan viewer
          Center(
            child: Hero(
              tag: heroTag,
              child: InteractiveViewer(
                minScale: 0.5,
                maxScale: 5.0,
                child: CachedNetworkImage(
                  imageUrl: imageUrl,
                  fit: BoxFit.contain,
                  placeholder: (_, _) => const Center(
                    child: CircularProgressIndicator(color: Colors.white),
                  ),
                  errorWidget: (_, _, _) => const Icon(
                    Icons.broken_image,
                    color: Colors.white54,
                    size: 64,
                  ),
                ),
              ),
            ),
          ),
          // Close button
          SafeArea(
            child: Align(
              alignment: Alignment.topRight,
              child: Padding(
                padding: const EdgeInsets.all(8),
                child: IconButton(
                  onPressed: () => Navigator.of(context).pop(),
                  icon: const Icon(Icons.close, color: Colors.white, size: 28),
                  style: IconButton.styleFrom(
                    backgroundColor: Colors.black45,
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
