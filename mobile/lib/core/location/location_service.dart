import 'package:geolocator/geolocator.dart';

/// Result of asking the device where it is.
///
/// A failure carries a message rather than throwing, because every caller
/// renders it in the same place: a status card above the submit button.
class DeviceLocation {
  final Position? position;
  final String? error;

  const DeviceLocation._(this.position, this.error);

  const DeviceLocation.found(Position position) : this._(position, null);
  const DeviceLocation.failed(String error) : this._(null, error);

  bool get isAvailable => position != null;
}

/// Request permission if needed, then read the current position.
///
/// Extracted from the copies that lived in `submit_sighting_screen.dart` and
/// `declare_lost_screen.dart` so both screens ask for location the same way.
Future<DeviceLocation> getDeviceLocation() async {
  try {
    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever) {
      return const DeviceLocation.failed('Location permission denied.');
    }

    final position = await Geolocator.getCurrentPosition(
      locationSettings: const LocationSettings(accuracy: LocationAccuracy.high),
    );
    return DeviceLocation.found(position);
  } catch (e) {
    return DeviceLocation.failed(e.toString());
  }
}
