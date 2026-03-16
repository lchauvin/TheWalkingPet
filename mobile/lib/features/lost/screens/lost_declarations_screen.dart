import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/lost_provider.dart';
import '../models/lost_declaration.dart';
import '../../pets/providers/pets_provider.dart';

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

    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
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
                    color: statusColor.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: statusColor),
                  ),
                  child: Text(d.status,
                      style: TextStyle(color: statusColor, fontSize: 12)),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Text('Search radius: ${d.searchRadiusKm} km',
                style: const TextStyle(color: Colors.grey)),
            if (d.rewardAmount != null)
              Text('Reward: \$${d.rewardAmount!.toStringAsFixed(2)}',
                  style: const TextStyle(color: Colors.green)),
            if (d.description != null && d.description!.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(d.description!),
              ),
            if (d.isActive) ...[
              const SizedBox(height: 10),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  OutlinedButton.icon(
                    onPressed: () async {
                      final confirmed = await showDialog<bool>(
                        context: context,
                        builder: (ctx) => AlertDialog(
                          title: const Text('Mark as Found'),
                          content:
                              Text('Mark $petName as found?'),
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
                        await ref
                            .read(lostProvider.notifier)
                            .markFound(d.id);
                      }
                    },
                    icon: const Icon(Icons.check_circle_outline,
                        color: Colors.green),
                    label: const Text('Found!',
                        style: TextStyle(color: Colors.green)),
                  ),
                  const SizedBox(width: 8),
                  OutlinedButton.icon(
                    onPressed: () async {
                      final confirmed = await showDialog<bool>(
                        context: context,
                        builder: (ctx) => AlertDialog(
                          title: const Text('Cancel Declaration'),
                          content: const Text(
                              'Cancel this lost declaration?'),
                          actions: [
                            TextButton(
                              onPressed: () => Navigator.pop(ctx, false),
                              child: const Text('No'),
                            ),
                            TextButton(
                              onPressed: () => Navigator.pop(ctx, true),
                              style: TextButton.styleFrom(
                                  foregroundColor: Colors.red),
                              child: const Text('Yes, Cancel'),
                            ),
                          ],
                        ),
                      );
                      if (confirmed == true) {
                        await ref
                            .read(lostProvider.notifier)
                            .cancel(d.id);
                      }
                    },
                    icon: const Icon(Icons.cancel_outlined,
                        color: Colors.red),
                    label: const Text('Cancel',
                        style: TextStyle(color: Colors.red)),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}
