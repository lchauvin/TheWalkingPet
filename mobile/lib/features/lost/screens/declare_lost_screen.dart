import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:go_router/go_router.dart';
import '../providers/lost_provider.dart';

class DeclareLostScreen extends ConsumerStatefulWidget {
  final String petId;
  final String petName;

  const DeclareLostScreen({
    super.key,
    required this.petId,
    required this.petName,
  });

  @override
  ConsumerState<DeclareLostScreen> createState() => _DeclareLostScreenState();
}

class _DeclareLostScreenState extends ConsumerState<DeclareLostScreen> {
  final _descCtrl = TextEditingController();
  final _rewardCtrl = TextEditingController();
  Position? _position;
  bool _locating = false;
  bool _submitting = false;
  String? _locationError;

  @override
  void initState() {
    super.initState();
    _getLocation();
  }

  @override
  void dispose() {
    _descCtrl.dispose();
    _rewardCtrl.dispose();
    super.dispose();
  }

  Future<void> _getLocation() async {
    setState(() { _locating = true; _locationError = null; });
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
        locationSettings: const LocationSettings(accuracy: LocationAccuracy.high),
      );
      setState(() { _position = pos; _locating = false; });
    } catch (e) {
      setState(() { _locationError = e.toString(); _locating = false; });
    }
  }

  Future<void> _submit() async {
    if (_position == null) return;
    setState(() => _submitting = true);

    final reward = double.tryParse(_rewardCtrl.text.trim());
    final decl = await ref.read(lostProvider.notifier).declare(
      petId: widget.petId,
      lat: _position!.latitude,
      lon: _position!.longitude,
      description: _descCtrl.text.trim(),
      rewardAmount: reward,
    );

    if (mounted) {
      setState(() => _submitting = false);
      if (decl != null) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('${widget.petName} declared as lost.')),
        );
        context.pop();
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to declare lost. Try again.')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Declare ${widget.petName} Lost')),
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
                      'Your current GPS location will be used as the last known position of your pet. '
                      'This helps narrow the search area and maximizes the chances of finding them.',
                      style: TextStyle(color: Colors.blue, fontSize: 13),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Location status
            Card(
              color: _position != null
                  ? Colors.green.shade50
                  : _locationError != null
                      ? Colors.red.shade50
                      : Colors.orange.shade50,
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Row(
                  children: [
                    _locating
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : Icon(
                            _position != null
                                ? Icons.location_on
                                : Icons.location_off,
                            color: _position != null ? Colors.green : Colors.red,
                          ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _locating
                          ? const Text('Getting your location...')
                          : _position != null
                              ? Text(
                                  'Location: ${_position!.latitude.toStringAsFixed(5)}, '
                                  '${_position!.longitude.toStringAsFixed(5)}',
                                )
                              : Text(_locationError ?? 'Location unavailable'),
                    ),
                    if (!_locating && _position == null)
                      TextButton(
                        onPressed: _getLocation,
                        child: const Text('Retry'),
                      ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _descCtrl,
              maxLines: 3,
              decoration: const InputDecoration(
                labelText: 'Additional details (optional)',
                hintText: 'Last seen near... wearing collar...',
                prefixIcon: Icon(Icons.notes_outlined),
                border: OutlineInputBorder(),
                alignLabelWithHint: true,
              ),
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _rewardCtrl,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(
                labelText: 'Reward amount (optional)',
                prefixIcon: Icon(Icons.attach_money),
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: (_position == null || _submitting) ? null : _submit,
              icon: _submitting
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white),
                    )
                  : const Icon(Icons.warning_amber_rounded),
              label: const Text('Declare Lost', style: TextStyle(fontSize: 16)),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 14),
                backgroundColor: Colors.red,
                foregroundColor: Colors.white,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
