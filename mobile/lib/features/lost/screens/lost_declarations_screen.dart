import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';
import '../providers/lost_provider.dart';
import '../models/lost_declaration.dart';
import '../../pets/providers/pets_provider.dart';
import '../../matches/providers/matches_provider.dart';
import '../../matches/models/match.dart';

class LostDeclarationsScreen extends ConsumerWidget {
  const LostDeclarationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final lostAsync = ref.watch(lostProvider);
    final petsAsync = ref.watch(petsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Lost Pets'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.read(lostProvider.notifier).load(),
          ),
        ],
      ),
      body: lostAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
        data: (declarations) {
          final active = declarations.where((d) => d.isActive).toList();
          final past = declarations.where((d) => !d.isActive).toList();

          if (declarations.isEmpty) {
            return const Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.search_off, size: 64, color: Colors.grey),
                  SizedBox(height: 8),
                  Text('No lost declarations', style: TextStyle(color: Colors.grey)),
                ],
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: () => ref.read(lostProvider.notifier).load(),
            child: ListView(
              padding: const EdgeInsets.all(12),
              children: [
                if (active.isNotEmpty) ...[
                  const _SectionHeader('Active'),
                  ...active.map((d) => _DeclarationCard(
                        declaration: d,
                        petName: petsAsync.valueOrNull
                                ?.where((p) => p.id == d.petId)
                                .firstOrNull
                                ?.name ??
                            'Unknown',
                      )),
                ],
                if (past.isNotEmpty) ...[
                  const _SectionHeader('Past'),
                  ...past.map((d) => _DeclarationCard(
                        declaration: d,
                        petName: petsAsync.valueOrNull
                                ?.where((p) => p.id == d.petId)
                                .firstOrNull
                                ?.name ??
                            'Unknown',
                      )),
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

class _DeclarationCard extends ConsumerWidget {
  final LostDeclaration declaration;
  final String petName;

  const _DeclarationCard({required this.declaration, required this.petName});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final d = declaration;
    final statusColor = d.status == 'ACTIVE'
        ? Colors.red
        : d.status == 'FOUND'
            ? Colors.green
            : Colors.grey;

    // Confirmed sightings for this declaration, sorted oldest→newest
    final confirmedSightings = (ref.watch(matchesProvider).valueOrNull ?? [])
        .where((m) =>
            m.lostDeclarationId == d.id &&
            m.isConfirmed &&
            m.sightingLat != null &&
            m.sightingLon != null)
        .toList()
      ..sort((a, b) => a.createdAt.compareTo(b.createdAt));

    final hasActions = d.isActive || confirmedSightings.isNotEmpty;

    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── Main content ──────────────────────────────────
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 14, 14, 10),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Name + status badge
                Row(
                  children: [
                    Expanded(
                      child: Text(petName,
                          style: const TextStyle(
                              fontWeight: FontWeight.bold, fontSize: 16)),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: statusColor.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: statusColor),
                      ),
                      child: Text(d.status,
                          style:
                              TextStyle(color: statusColor, fontSize: 12)),
                    ),
                  ],
                ),
                const SizedBox(height: 8),

                // Info chips row
                Wrap(
                  spacing: 12,
                  children: [
                    _InfoChip(
                      icon: Icons.radar,
                      label: '${d.searchRadiusKm} km radius',
                    ),
                    if (d.rewardAmount != null)
                      _InfoChip(
                        icon: Icons.monetization_on_outlined,
                        label:
                            '\$${d.rewardAmount!.toStringAsFixed(0)} reward',
                        color: Colors.green,
                      ),
                  ],
                ),

                // Description
                if (d.description != null && d.description!.isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Text(d.description!,
                      style: const TextStyle(
                          color: Colors.black87, fontSize: 13)),
                ],
              ],
            ),
          ),

          // ── Action row ────────────────────────────────────
          if (hasActions) ...[
            const Divider(height: 1),
            Padding(
              padding:
                  const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              child: Row(
                children: [
                  // Left: sightings path
                  if (confirmedSightings.isNotEmpty)
                    TextButton.icon(
                      onPressed: () => _showSightingsPath(
                          context, petName, confirmedSightings),
                      icon: const Icon(Icons.route, size: 18),
                      label: Text(
                          '${confirmedSightings.length} sighting${confirmedSightings.length > 1 ? 's' : ''}'),
                      style: TextButton.styleFrom(
                          foregroundColor: Colors.deepOrange),
                    ),

                  const Spacer(),

                  // Right: found / cancel
                  if (d.isActive) ...[
                    TextButton.icon(
                      onPressed: () => _confirmMarkFound(context, ref, d),
                      icon: const Icon(Icons.check_circle_outline, size: 18),
                      label: const Text('Found'),
                      style: TextButton.styleFrom(
                          foregroundColor: Colors.green),
                    ),
                    TextButton.icon(
                      onPressed: () => _confirmCancel(context, ref, d),
                      icon: const Icon(Icons.cancel_outlined, size: 18),
                      label: const Text('Cancel'),
                      style:
                          TextButton.styleFrom(foregroundColor: Colors.red),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Future<void> _confirmMarkFound(
      BuildContext context, WidgetRef ref, LostDeclaration d) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Mark as Found'),
        content: Text('Mark $petName as found?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Confirm'),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      await ref.read(lostProvider.notifier).markFound(d.id);
    }
  }

  Future<void> _confirmCancel(
      BuildContext context, WidgetRef ref, LostDeclaration d) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Cancel Declaration'),
        content: const Text('Cancel this lost declaration?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('No'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Yes, Cancel'),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      await ref.read(lostProvider.notifier).cancel(d.id);
    }
  }

  void _showSightingsPath(
      BuildContext context, String petName, List<PetMatch> sightings) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (_) => _SightingsPathSheet(
        petName: petName,
        sightings: sightings,
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;

  const _InfoChip({
    required this.icon,
    required this.label,
    this.color = Colors.grey,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 13, color: color),
        const SizedBox(width: 3),
        Text(label, style: TextStyle(fontSize: 12, color: color)),
      ],
    );
  }
}

class _SightingsPathSheet extends StatelessWidget {
  final String petName;
  final List<PetMatch> sightings;

  const _SightingsPathSheet({
    required this.petName,
    required this.sightings,
  });

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      initialChildSize: 0.6,
      minChildSize: 0.4,
      maxChildSize: 0.92,
      expand: false,
      builder: (_, scrollController) {
        return Column(
          children: [
            // Handle
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 12),
              child: Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: Colors.grey.shade300,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),

            // Header
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
              child: Row(
                children: [
                  const Icon(Icons.route, color: Colors.deepOrange),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '$petName — Sightings Path',
                          style: const TextStyle(
                              fontWeight: FontWeight.bold, fontSize: 16),
                        ),
                        Text(
                          '${sightings.length} confirmed sighting${sightings.length > 1 ? 's' : ''} · oldest to newest',
                          style: const TextStyle(
                              color: Colors.grey, fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

            const Divider(height: 1),

            // Timeline list
            Expanded(
              child: ListView.builder(
                controller: scrollController,
                padding: const EdgeInsets.symmetric(
                    horizontal: 16, vertical: 8),
                itemCount: sightings.length,
                itemBuilder: (context, i) {
                  final s = sightings[i];
                  final isLast = i == sightings.length - 1;
                  return _SightingTimelineItem(
                    sighting: s,
                    index: i + 1,
                    isLast: isLast,
                  );
                },
              ),
            ),

            // Full path button
            if (sightings.length > 1)
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
                child: ElevatedButton.icon(
                  onPressed: () => _openFullPath(sightings),
                  icon: const Icon(Icons.map_outlined),
                  label: const Text('Show Full Path in Maps'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.deepOrange,
                    foregroundColor: Colors.white,
                    minimumSize: const Size(double.infinity, 44),
                  ),
                ),
              )
            else
              const SizedBox(height: 16),
          ],
        );
      },
    );
  }

  Future<void> _openFullPath(List<PetMatch> sightings) async {
    // Google Maps directions URL with all waypoints
    final waypoints = sightings
        .map((s) => '${s.sightingLat},${s.sightingLon}')
        .join('/');
    final uri = Uri.parse(
        'https://www.google.com/maps/dir/$waypoints');
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }
}

class _SightingTimelineItem extends StatelessWidget {
  final PetMatch sighting;
  final int index;
  final bool isLast;

  const _SightingTimelineItem({
    required this.sighting,
    required this.index,
    required this.isLast,
  });

  @override
  Widget build(BuildContext context) {
    final dt = sighting.createdAt.toLocal();
    final dateStr =
        '${dt.day.toString().padLeft(2, '0')}/${dt.month.toString().padLeft(2, '0')}/${dt.year}';
    final timeStr =
        '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';

    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Timeline indicator column
          SizedBox(
            width: 32,
            child: Column(
              children: [
                Container(
                  width: 28,
                  height: 28,
                  decoration: BoxDecoration(
                    color: index == 1
                        ? Colors.orange
                        : isLast
                            ? Colors.deepOrange
                            : Colors.deepOrange.shade200,
                    shape: BoxShape.circle,
                  ),
                  child: Center(
                    child: Text(
                      '$index',
                      style: const TextStyle(
                          color: Colors.white,
                          fontSize: 12,
                          fontWeight: FontWeight.bold),
                    ),
                  ),
                ),
                if (!isLast)
                  Expanded(
                    child: Container(
                      width: 2,
                      color: Colors.deepOrange.shade100,
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(width: 12),

          // Sighting info
          Expanded(
            child: Padding(
              padding: EdgeInsets.only(bottom: isLast ? 0 : 16),
              child: Container(
                margin: const EdgeInsets.only(bottom: 4),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.grey.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.grey.shade200),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.calendar_today,
                            size: 14, color: Colors.grey),
                        const SizedBox(width: 4),
                        Text('$dateStr at $timeStr',
                            style: const TextStyle(
                                fontWeight: FontWeight.w600, fontSize: 13)),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Row(
                      children: [
                        const Icon(Icons.location_on,
                            size: 14, color: Colors.grey),
                        const SizedBox(width: 4),
                        Text(
                          '${sighting.sightingLat!.toStringAsFixed(5)}, '
                          '${sighting.sightingLon!.toStringAsFixed(5)}',
                          style: const TextStyle(
                              color: Colors.grey, fontSize: 12),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    GestureDetector(
                      onTap: () => _openInMaps(
                          sighting.sightingLat!, sighting.sightingLon!),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.open_in_new,
                              size: 14, color: Colors.deepOrange),
                          const SizedBox(width: 4),
                          const Text('Open in Maps',
                              style: TextStyle(
                                  color: Colors.deepOrange,
                                  fontSize: 12,
                                  decoration: TextDecoration.underline)),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _openInMaps(double lat, double lon) async {
    final uri = Uri.parse(
        'https://www.google.com/maps/search/?api=1&query=$lat,$lon');
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }
}
