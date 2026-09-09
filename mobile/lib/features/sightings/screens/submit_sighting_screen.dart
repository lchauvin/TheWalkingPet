import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import '../../../core/api/sightings_api.dart';
import '../../../core/location/location_resolution.dart';
import '../../../core/location/location_service.dart';
import '../../../core/location/photo_metadata.dart';
import '../models/sighting.dart';

class SubmitSightingScreen extends ConsumerStatefulWidget {
  const SubmitSightingScreen({super.key});

  @override
  ConsumerState<SubmitSightingScreen> createState() =>
      _SubmitSightingScreenState();
}

class _SubmitSightingScreenState extends ConsumerState<SubmitSightingScreen> {
  final _picker = ImagePicker();
  final _api = SightingsApi();

  File? _image;

  /// The device's own fix, kept so the conflict prompt can offer it.
  LatLng? _devicePosition;

  /// What will actually be submitted, once EXIF and the device are reconciled.
  LatLng? _position;
  LocationSource? _source;
  DateTime? _takenAt;

  bool _locating = false;
  bool _submitting = false;
  String? _locationError;
  Sighting? _result;

  @override
  void initState() {
    super.initState();
    // Fetched up front so the location card is populated before a photo is
    // chosen; it is fetched again at pick time, when it actually matters.
    _refreshDeviceLocation();
  }

  Future<void> _refreshDeviceLocation() async {
    setState(() {
      _locating = true;
      _locationError = null;
    });

    final result = await getDeviceLocation();
    if (!mounted) return;

    setState(() {
      _locating = false;
      _locationError = result.error;
      _devicePosition = result.isAvailable
          ? LatLng(result.position!.latitude, result.position!.longitude)
          : null;

      // Nothing has been picked yet, so the device fix is the working answer.
      if (_image == null) {
        _position = _devicePosition;
        _source = _devicePosition == null ? null : LocationSource.device;
      }
    });
  }

  Future<void> _pickImage(ImageSource source) async {
    // Must precede the pick: Android decides whether to redact the file's GPS
    // at the moment it hands it over, so asking afterwards is too late.
    if (source == ImageSource.gallery) {
      await ensureMediaLocationAccess();
    }

    // No imageQuality: re-encoding strips the EXIF this screen depends on.
    final picked = await _picker.pickImage(source: source);
    if (picked == null) return;

    setState(() {
      _image = File(picked.path);
      _result = null;
      _position = null;
      _source = null;
      _takenAt = null;
    });

    await _resolveLocationForPickedImage();
  }

  /// Reconcile where the photo says it was taken with where the reporter is.
  Future<void> _resolveLocationForPickedImage() async {
    // Re-read the device position now rather than trusting the one captured
    // when the screen opened — the reporter may have moved since.
    await _refreshDeviceLocation();
    if (!mounted || _image == null) return;

    final metadata = await readPhotoMetadata(_image!);
    if (!mounted) return;

    // Set before resolving: the staleness notice renders off this even when the
    // reporter dismisses the conflict prompt without settling on a location.
    setState(() => _takenAt = metadata.takenAt);

    final resolution = resolveSightingLocation(
      exif: metadata.position,
      device: _devicePosition,
      takenAt: metadata.takenAt,
    );

    switch (resolution) {
      case UseLocation(:final position, :final source):
        setState(() {
          _position = position;
          _source = source;
        });
      case NoLocation():
        setState(() {
          _position = null;
          _source = null;
        });
      case NeedsUserChoice():
        final choice = await _askWhichLocation(resolution);
        if (!mounted) return;
        // Dismissed without choosing: leave it unresolved rather than guessing.
        if (choice == null) return;
        setState(() {
          _source = choice;
          _position = choice == LocationSource.exif
              ? resolution.exif
              : resolution.device;
        });
    }
  }

  /// The photo and the phone disagree by enough to change which pets are
  /// searched, so the reporter decides instead of us.
  Future<LocationSource?> _askWhichLocation(NeedsUserChoice conflict) {
    final distance = _formatDistance(conflict.distanceKm);

    return showModalBottomSheet<LocationSource>(
      context: context,
      isScrollControlled: true,
      builder: (_) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 20, 20, 4),
              child: Text(
                'Where was this pet seen?',
                style: Theme.of(context).textTheme.titleMedium,
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 12),
              child: Text(
                'This photo was taken $distance from where you are now. '
                'Picking the wrong one searches the wrong neighbourhood.',
                style: TextStyle(color: Colors.grey.shade600, fontSize: 13),
              ),
            ),
            ListTile(
              leading: const Icon(Icons.photo_camera_back_outlined,
                  color: Colors.deepOrange),
              title: const Text('Where the photo was taken'),
              subtitle: Text(
                _takenAt == null
                    ? '${conflict.exif}'
                    : '${conflict.exif}\nTaken ${_formatWhen(_takenAt!)}',
              ),
              isThreeLine: _takenAt != null,
              onTap: () => Navigator.pop(context, LocationSource.exif),
            ),
            ListTile(
              leading: const Icon(Icons.my_location),
              title: const Text('Where I am now'),
              subtitle: Text('${conflict.device}'),
              onTap: () => Navigator.pop(context, LocationSource.device),
            ),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
  }

  static String _formatDistance(double km) =>
      km < 1 ? '${(km * 1000).round()} m' : '${km.toStringAsFixed(1)} km';

  static String _formatWhen(DateTime when) {
    final days = DateTime.now().difference(when).inDays;
    if (days < 1) return 'today';
    if (days == 1) return 'yesterday';
    if (days < 30) return '$days days ago';
    final months = (days / 30).floor();
    return months == 1 ? 'a month ago' : '$months months ago';
  }

  Future<void> _submit() async {
    final position = _position;
    final source = _source;
    if (_image == null || position == null || source == null) return;
    setState(() => _submitting = true);

    try {
      final sighting = await _api.submit(
        image: _image!,
        latitude: position.latitude,
        longitude: position.longitude,
        source: source,
        takenAt: _takenAt,
      );
      setState(() {
        _result = sighting;
        _submitting = false;
      });
    } catch (e) {
      setState(() => _submitting = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to submit sighting. Please try again.')),
        );
      }
    }
  }

  void _reset() {
    setState(() {
      _image = null;
      _result = null;
      _takenAt = null;
      _position = _devicePosition;
      _source = _devicePosition == null ? null : LocationSource.device;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_result != null) return _buildSuccess();

    final stale = isStalePhoto(_takenAt);

    return Scaffold(
      appBar: AppBar(title: const Text('Report a Sighting')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Info banner
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.blue.shade50,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.blue.shade200),
              ),
              child: const Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.info_outline, color: Colors.blue, size: 20),
                  SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      'Spotted a pet roaming alone? Take a photo — we\'ll automatically compare it against lost pets nearby.',
                      style: TextStyle(color: Colors.blue, fontSize: 13),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Photo picker
            GestureDetector(
              onTap: () => _showSourcePicker(),
              child: Container(
                height: 220,
                decoration: BoxDecoration(
                  color: Colors.grey.shade100,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.grey.shade300, width: 2),
                ),
                child: _image != null
                    ? ClipRRect(
                        borderRadius: BorderRadius.circular(10),
                        child: Image.file(_image!, fit: BoxFit.cover),
                      )
                    : Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.add_a_photo_outlined,
                              size: 56, color: Colors.grey.shade400),
                          const SizedBox(height: 8),
                          Text('Tap to take or choose a photo',
                              style: TextStyle(color: Colors.grey.shade500)),
                        ],
                      ),
              ),
            ),
            const SizedBox(height: 16),

            // Location status
            _LocationTile(
              locating: _locating,
              position: _position,
              source: _source,
              error: _locationError,
              onRetry: _image == null
                  ? _refreshDeviceLocation
                  : _resolveLocationForPickedImage,
            ),

            if (stale) ...[
              const SizedBox(height: 12),
              _StaleNotice(takenAt: _takenAt!),
            ],

            const SizedBox(height: 24),

            ElevatedButton.icon(
              onPressed:
                  (_image == null || _position == null || _submitting)
                      ? null
                      : _submit,
              icon: _submitting
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white),
                    )
                  : const Icon(Icons.send_outlined),
              label: Text(
                _submitting ? 'Submitting...' : 'Submit Sighting',
                style: const TextStyle(fontSize: 16),
              ),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 14),
                backgroundColor: Colors.deepOrange,
                foregroundColor: Colors.white,
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _showSourcePicker() {
    showModalBottomSheet(
      context: context,
      builder: (_) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.camera_alt_outlined),
              title: const Text('Take a photo'),
              onTap: () {
                Navigator.pop(context);
                _pickImage(ImageSource.camera);
              },
            ),
            ListTile(
              leading: const Icon(Icons.photo_library_outlined),
              title: const Text('Choose from gallery'),
              onTap: () {
                Navigator.pop(context);
                _pickImage(ImageSource.gallery);
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSuccess() {
    final species = _result!.speciesDetected;
    return Scaffold(
      appBar: AppBar(title: const Text('Sighting Submitted')),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.check_circle, color: Colors.green, size: 80),
              const SizedBox(height: 16),
              const Text(
                'Thank you!',
                style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              Text(
                species != null
                    ? 'We detected a ${species.toLowerCase()} and are checking for matches nearby.'
                    : 'Your sighting has been submitted. We\'re checking for matches nearby.',
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.grey),
              ),
              const SizedBox(height: 32),
              ElevatedButton.icon(
                onPressed: _reset,
                icon: const Icon(Icons.add_a_photo_outlined),
                label: const Text('Report Another'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.deepOrange,
                  foregroundColor: Colors.white,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _LocationTile extends StatelessWidget {
  final bool locating;
  final LatLng? position;
  final LocationSource? source;
  final String? error;
  final VoidCallback onRetry;

  const _LocationTile({
    required this.locating,
    required this.position,
    required this.source,
    required this.error,
    required this.onRetry,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      color: position != null
          ? Colors.green.shade50
          : error != null
              ? Colors.red.shade50
              : Colors.orange.shade50,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            locating
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : Icon(
                    position != null
                        ? (source == LocationSource.exif
                            ? Icons.photo_camera_back_outlined
                            : Icons.location_on)
                        : Icons.location_off,
                    color: position != null ? Colors.green : Colors.red,
                  ),
            const SizedBox(width: 12),
            Expanded(
              child: locating
                  ? const Text('Getting your location...')
                  : position != null
                      // Which source won stays visible right up to submitting.
                      ? Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              source == LocationSource.exif
                                  ? 'From the photo'
                                  : 'Your current location',
                              style: const TextStyle(
                                  fontWeight: FontWeight.w600, fontSize: 13),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              '$position',
                              style: TextStyle(
                                  color: Colors.grey.shade700, fontSize: 12),
                            ),
                          ],
                        )
                      : Text(error ?? 'Location unavailable'),
            ),
            if (!locating && position == null)
              TextButton(onPressed: onRetry, child: const Text('Retry')),
            if (!locating && position != null)
              TextButton(onPressed: onRetry, child: const Text('Change')),
          ],
        ),
      ),
    );
  }
}

/// Shown when the photo is old enough that the pet has probably moved on.
class _StaleNotice extends StatelessWidget {
  final DateTime takenAt;

  const _StaleNotice({required this.takenAt});

  @override
  Widget build(BuildContext context) {
    final days = DateTime.now().difference(takenAt).inDays;
    final age = days < 30
        ? '$days days old'
        : '${(days / 30).floor()} month${days < 60 ? '' : 's'} old';

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.amber.shade50,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.amber.shade300),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.schedule, color: Colors.amber.shade800, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              'This photo is $age. It is still worth reporting, but the pet '
              'may have moved on since.',
              style: TextStyle(color: Colors.amber.shade900, fontSize: 13),
            ),
          ),
        ],
      ),
    );
  }
}
