import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:image_picker/image_picker.dart';
import '../../../core/api/sightings_api.dart';
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
  Position? _position;
  bool _locating = false;
  bool _submitting = false;
  String? _locationError;
  Sighting? _result;

  @override
  void initState() {
    super.initState();
    _getLocation();
  }

  Future<void> _getLocation() async {
    setState(() {
      _locating = true;
      _locationError = null;
    });
    try {
      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.deniedForever ||
          permission == LocationPermission.denied) {
        setState(() {
          _locationError = 'Location permission denied.';
          _locating = false;
        });
        return;
      }
      final pos = await Geolocator.getCurrentPosition(
        locationSettings:
            const LocationSettings(accuracy: LocationAccuracy.high),
      );
      if (mounted) setState(() { _position = pos; _locating = false; });
    } catch (e) {
      if (mounted) setState(() { _locationError = e.toString(); _locating = false; });
    }
  }

  Future<void> _pickImage(ImageSource source) async {
    final picked = await _picker.pickImage(source: source, imageQuality: 85);
    if (picked != null) {
      setState(() {
        _image = File(picked.path);
        _result = null;
      });
    }
  }

  Future<void> _submit() async {
    if (_image == null || _position == null) return;
    setState(() => _submitting = true);

    try {
      final sighting = await _api.submit(
        image: _image!,
        latitude: _position!.latitude,
        longitude: _position!.longitude,
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
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_result != null) return _buildSuccess();

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
              error: _locationError,
              onRetry: _getLocation,
            ),
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
  final Position? position;
  final String? error;
  final VoidCallback onRetry;

  const _LocationTile({
    required this.locating,
    required this.position,
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
                    position != null ? Icons.location_on : Icons.location_off,
                    color: position != null ? Colors.green : Colors.red,
                  ),
            const SizedBox(width: 12),
            Expanded(
              child: locating
                  ? const Text('Getting your location...')
                  : position != null
                      ? Text(
                          'Location: ${position!.latitude.toStringAsFixed(5)}, '
                          '${position!.longitude.toStringAsFixed(5)}',
                        )
                      : Text(error ?? 'Location unavailable'),
            ),
            if (!locating && position == null)
              TextButton(onPressed: onRetry, child: const Text('Retry')),
          ],
        ),
      ),
    );
  }
}
