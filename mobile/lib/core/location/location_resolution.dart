import 'dart:math' as math;

/// Where a sighting's coordinates came from. Mirrors the backend
/// `LocationSource` enum in `src/db/models.py`.
enum LocationSource {
  exif,
  device;

  /// The wire value the API expects on the `location_source` form field.
  String get wireValue => this == LocationSource.exif ? 'EXIF' : 'DEVICE';
}

/// How far the photo's own location may sit from the reporter's current
/// position before we stop guessing and ask.
///
/// A lost declaration's default `search_radius_km` is 0.5, so a discrepancy
/// approaching that size can change which pets are even considered candidates.
/// Typical GPS error (10-50 m) stays comfortably below this, so agreeing
/// sources do not nag the user.
const kLocationConflictThresholdKm = 0.25;

/// Past this age, a photo is old enough that the pet has likely moved on and
/// the reporter should be told before submitting.
const kStalePhotoWarningDays = 7;

const _earthRadiusKm = 6371.0;

class LatLng {
  final double latitude;
  final double longitude;

  const LatLng(this.latitude, this.longitude);

  @override
  bool operator ==(Object other) =>
      other is LatLng &&
      other.latitude == latitude &&
      other.longitude == longitude;

  @override
  int get hashCode => Object.hash(latitude, longitude);

  @override
  String toString() =>
      '${latitude.toStringAsFixed(5)}, ${longitude.toStringAsFixed(5)}';
}

/// Great-circle distance in km. Ports `haversine_km` from `src/utils/geo.py`
/// so the client and the matching pipeline measure distance identically.
double haversineKm(LatLng a, LatLng b) {
  double toRad(double deg) => deg * math.pi / 180.0;

  final phi1 = toRad(a.latitude);
  final phi2 = toRad(b.latitude);
  final dPhi = toRad(b.latitude - a.latitude);
  final dLambda = toRad(b.longitude - a.longitude);

  final h = math.pow(math.sin(dPhi / 2), 2) +
      math.cos(phi1) * math.cos(phi2) * math.pow(math.sin(dLambda / 2), 2);
  return 2 * _earthRadiusKm * math.asin(math.sqrt(h.toDouble()));
}

/// The outcome of reconciling a photo's embedded location with the device's.
sealed class LocationResolution {
  const LocationResolution();
}

/// A location was settled on without troubling the user.
class UseLocation extends LocationResolution {
  final LatLng position;
  final LocationSource source;

  const UseLocation(this.position, this.source);
}

/// The two sources disagree by more than [kLocationConflictThresholdKm];
/// the reporter has to pick one.
class NeedsUserChoice extends LocationResolution {
  final LatLng exif;
  final LatLng device;
  final double distanceKm;
  final DateTime? takenAt;

  const NeedsUserChoice({
    required this.exif,
    required this.device,
    required this.distanceKm,
    this.takenAt,
  });
}

/// Neither source produced a location, so there is nothing to submit.
class NoLocation extends LocationResolution {
  const NoLocation();
}

/// Decide which location a sighting should carry.
///
/// EXIF wins where it exists — it describes where the photo was actually
/// taken, whereas the device only knows where the reporter is standing now.
/// The exception is a large disagreement, which is ambiguous enough that
/// guessing either way risks filing the sighting in the wrong place.
LocationResolution resolveSightingLocation({
  required LatLng? exif,
  required LatLng? device,
  DateTime? takenAt,
}) {
  if (exif == null) {
    return device == null
        ? const NoLocation()
        : UseLocation(device, LocationSource.device);
  }

  if (device == null) return UseLocation(exif, LocationSource.exif);

  final distanceKm = haversineKm(exif, device);
  if (distanceKm > kLocationConflictThresholdKm) {
    return NeedsUserChoice(
      exif: exif,
      device: device,
      distanceKm: distanceKm,
      takenAt: takenAt,
    );
  }
  return UseLocation(exif, LocationSource.exif);
}

/// Whether a photo is old enough to warn the reporter about.
bool isStalePhoto(DateTime? takenAt, {DateTime? now}) {
  if (takenAt == null) return false;
  final reference = now ?? DateTime.now();
  return reference.difference(takenAt).inDays >= kStalePhotoWarningDays;
}
