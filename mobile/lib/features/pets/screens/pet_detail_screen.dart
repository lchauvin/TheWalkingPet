import 'dart:io';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import 'package:go_router/go_router.dart';
import '../../../core/api/api_client.dart';
import '../providers/pets_provider.dart';
import '../models/pet.dart';
import '../../lost/providers/lost_provider.dart';

class PetDetailScreen extends ConsumerWidget {
  final String petId;
  const PetDetailScreen({super.key, required this.petId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final petsAsync = ref.watch(petsProvider);

    return petsAsync.when(
      loading: () => const Scaffold(body: Center(child: CircularProgressIndicator())),
      error: (e, _) => const Scaffold(body: Center(child: Text('Failed to load pet details.'))),
      data: (pets) {
        final pet = pets.where((p) => p.id == petId).firstOrNull;
        if (pet == null) {
          return const Scaffold(body: Center(child: Text('Pet not found')));
        }
        return _PetDetailView(pet: pet);
      },
    );
  }
}

class _PetDetailView extends ConsumerStatefulWidget {
  final Pet pet;
  const _PetDetailView({required this.pet});

  @override
  ConsumerState<_PetDetailView> createState() => _PetDetailViewState();
}

class _PetDetailViewState extends ConsumerState<_PetDetailView> {
  final _picker = ImagePicker();
  bool _uploading = false;
  int _uploadProgress = 0;
  int _uploadTotal = 0;

  Future<void> _pickAndUpload() async {
    final source = await showModalBottomSheet<ImageSource>(
      context: context,
      builder: (_) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.photo_library_outlined),
              title: const Text('Choose from gallery'),
              subtitle: const Text('Select multiple photos at once'),
              onTap: () => Navigator.pop(context, ImageSource.gallery),
            ),
            ListTile(
              leading: const Icon(Icons.camera_alt_outlined),
              title: const Text('Take a photo'),
              onTap: () => Navigator.pop(context, ImageSource.camera),
            ),
          ],
        ),
      ),
    );
    if (source == null) return;

    final remaining = 10 - widget.pet.images.length;

    if (source == ImageSource.gallery) {
      final picked = await _picker.pickMultiImage(imageQuality: 85, limit: remaining);
      if (picked.isEmpty || !mounted) return;

      setState(() {
        _uploading = true;
        _uploadProgress = 0;
        _uploadTotal = picked.length;
      });
      int failed = 0;
      try {
        for (final xfile in picked) {
          try {
            await ref.read(petsProvider.notifier).uploadImage(
              widget.pet.id,
              File(xfile.path),
              isPrimary: widget.pet.images.isEmpty && _uploadProgress == 0,
            );
          } catch (_) {
            failed++;
          }
          if (!mounted) return;
          setState(() => _uploadProgress++);
        }
      } finally {
        if (mounted) {
          setState(() => _uploading = false);
          if (failed > 0) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text('$failed photo${failed > 1 ? 's' : ''} failed to upload.'),
              ),
            );
          }
        }
      }
    } else {
      final picked = await _picker.pickImage(source: source, imageQuality: 85);
      if (picked == null || !mounted) return;

      setState(() { _uploading = true; _uploadProgress = 0; _uploadTotal = 1; });
      try {
        await ref.read(petsProvider.notifier).uploadImage(
          widget.pet.id,
          File(picked.path),
          isPrimary: widget.pet.images.isEmpty,
        );
      } catch (_) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Failed to upload photo. Please try again.')),
          );
        }
      } finally {
        if (mounted) setState(() => _uploading = false);
      }
    }
  }

  Future<void> _confirmDelete() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Delete Pet'),
        content: Text('Are you sure you want to delete ${widget.pet.name}?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (confirmed == true && mounted) {
      try {
        await ref.read(petsProvider.notifier).deletePet(widget.pet.id);
        if (!mounted) return;
        Navigator.of(context).pop();
      } catch (_) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to delete pet. Please try again.')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final pet = widget.pet;

    return Scaffold(
      appBar: AppBar(
        title: Text(pet.name),
        actions: [
          IconButton(
            icon: const Icon(Icons.delete_outline, color: Colors.red),
            onPressed: _confirmDelete,
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Info card
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _InfoRow(Icons.pets, 'Species', pet.species),
                  if (pet.breed != null) _InfoRow(Icons.category_outlined, 'Breed', pet.breed!),
                  if (pet.description != null)
                    _InfoRow(Icons.notes_outlined, 'Description', pet.description!),
                  _InfoRow(
                    Icons.qr_code,
                    'Microchipped',
                    pet.isMicrochipped ? 'Yes' : 'No',
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          _DeclareLostButton(pet: pet),
          const SizedBox(height: 16),

          // Photos section
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Photos (${pet.images.length})',
                  style: Theme.of(context).textTheme.titleMedium),
              _uploading
                  ? Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const SizedBox(
                          height: 16, width: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        ),
                        if (_uploadTotal > 1) ...[
                          const SizedBox(width: 6),
                          Text('$_uploadProgress/$_uploadTotal',
                              style: const TextStyle(fontSize: 12, color: Colors.grey)),
                        ],
                      ],
                    )
                  : widget.pet.images.length >= 10
                      ? const Text('Max 10 photos',
                          style: TextStyle(color: Colors.grey, fontSize: 12))
                      : TextButton.icon(
                          onPressed: _pickAndUpload,
                          icon: const Icon(Icons.add_photo_alternate_outlined),
                          label: const Text('Add Photo'),
                        ),
            ],
          ),
          const SizedBox(height: 8),

          if (pet.images.isEmpty)
            const Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Text('No photos yet. Add some to enable matching.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Colors.grey)),
              ),
            )
          else
            GridView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 3,
                crossAxisSpacing: 8,
                mainAxisSpacing: 8,
              ),
              itemCount: pet.images.length,
              itemBuilder: (context, i) {
                final img = pet.images[i];
                return Stack(
                  fit: StackFit.expand,
                  children: [
                    ClipRRect(
                      borderRadius: BorderRadius.circular(8),
                      child: CachedNetworkImage(
                        imageUrl: imageUrl(img.imagePath),
                        fit: BoxFit.cover,
                        placeholder: (_, _) => Container(
                          color: Colors.grey.shade100,
                          child: const Center(
                            child: CircularProgressIndicator(strokeWidth: 2),
                          ),
                        ),
                        errorWidget: (_, _, _) => Container(
                          color: Colors.grey.shade200,
                          child: const Icon(Icons.broken_image, color: Colors.grey),
                        ),
                      ),
                    ),
                    if (img.isPrimary)
                      Positioned(
                        top: 4,
                        left: 4,
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: Colors.deepOrange,
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: const Text('Main',
                              style: TextStyle(color: Colors.white, fontSize: 10)),
                        ),
                      ),
                    Positioned(
                      top: 2,
                      right: 2,
                      child: GestureDetector(
                        onTap: () async {
                          final confirmed = await showDialog<bool>(
                            context: context,
                            builder: (dialogContext) => AlertDialog(
                              title: const Text('Delete Photo'),
                              content: const Text('Remove this photo?'),
                              actions: [
                                TextButton(
                                  onPressed: () => Navigator.pop(dialogContext, false),
                                  child: const Text('Cancel'),
                                ),
                                TextButton(
                                  onPressed: () => Navigator.pop(dialogContext, true),
                                  style: TextButton.styleFrom(foregroundColor: Colors.red),
                                  child: const Text('Delete'),
                                ),
                              ],
                            ),
                          );
                          if (confirmed == true) {
                            try {
                              await ref
                                  .read(petsProvider.notifier)
                                  .deletePetImage(widget.pet.id, img.id);
                            } catch (_) {
                              if (context.mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(
                                    content: Text('Failed to delete photo. Please try again.'),
                                  ),
                                );
                              }
                            }
                          }
                        },
                        child: Container(
                          decoration: const BoxDecoration(
                            color: Colors.black54,
                            shape: BoxShape.circle,
                          ),
                          padding: const EdgeInsets.all(2),
                          child: const Icon(Icons.close, color: Colors.white, size: 14),
                        ),
                      ),
                    ),
                  ],
                );
              },
            ),
        ],
      ),
    );
  }
}

class _DeclareLostButton extends ConsumerWidget {
  final Pet pet;
  const _DeclareLostButton({required this.pet});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final lostAsync = ref.watch(lostProvider);
    final isAlreadyLost = lostAsync.valueOrNull
            ?.any((d) => d.petId == pet.id && d.isActive) ??
        false;

    if (isAlreadyLost) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
        decoration: BoxDecoration(
          color: Colors.orange.shade50,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: Colors.orange.shade300),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.warning_amber_rounded, color: Colors.orange.shade700, size: 20),
            const SizedBox(width: 8),
            Text(
              'Currently declared lost',
              style: TextStyle(
                color: Colors.orange.shade700,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      );
    }

    return ElevatedButton.icon(
      onPressed: () => context.push('/pets/${pet.id}/declare-lost', extra: pet.name),
      icon: const Icon(Icons.warning_amber_rounded),
      label: const Text('Declare Lost'),
      style: ElevatedButton.styleFrom(
        backgroundColor: Colors.red,
        foregroundColor: Colors.white,
        minimumSize: const Size(double.infinity, 44),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;

  const _InfoRow(this.icon, this.label, this.value);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          Icon(icon, size: 18, color: Colors.grey),
          const SizedBox(width: 8),
          Text('$label: ', style: const TextStyle(color: Colors.grey)),
          Expanded(child: Text(value)),
        ],
      ),
    );
  }
}
