import 'dart:math' as math;

import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/location/location_resolution.dart';

// Arc de Triomphe, and points a measured distance east of it.
const _base = LatLng(48.8584, 2.2945);

/// A point [metres] due east of [from], for exercising the threshold.
///
/// A degree of longitude shortens by cos(latitude) away from the equator;
/// at Paris that is a ~34% difference, so it cannot be skipped.
LatLng _eastOf(LatLng from, double metres) {
  const metresPerDegreeAtEquator = 111320.0;
  final scale =
      metresPerDegreeAtEquator * math.cos(from.latitude * math.pi / 180.0);
  return LatLng(from.latitude, from.longitude + metres / scale);
}

void main() {
  group('haversineKm', () {
    test('is zero for a point against itself', () {
      expect(haversineKm(_base, _base), 0);
    });

    test('matches a known distance', () {
      // Arc de Triomphe to Notre-Dame is about 4.3 km.
      const notreDame = LatLng(48.8530, 2.3499);
      expect(haversineKm(_base, notreDame), closeTo(4.1, 0.4));
    });

    test('is symmetric', () {
      const other = LatLng(48.8530, 2.3499);
      expect(haversineKm(_base, other), closeTo(haversineKm(other, _base), 1e-9));
    });

    test('handles crossing the equator and the prime meridian', () {
      const north = LatLng(1.0, 1.0);
      const south = LatLng(-1.0, -1.0);
      expect(haversineKm(north, south), greaterThan(300));
    });
  });

  group('resolveSightingLocation', () {
    test('prefers EXIF when both agree', () {
      final result = resolveSightingLocation(
        exif: _base,
        device: _eastOf(_base, 50),
      );
      expect(result, isA<UseLocation>());
      final use = result as UseLocation;
      expect(use.source, LocationSource.exif);
      expect(use.position, _base);
    });

    test('asks the user when they disagree beyond the threshold', () {
      final device = _eastOf(_base, 5000);
      final result = resolveSightingLocation(exif: _base, device: device);

      expect(result, isA<NeedsUserChoice>());
      final choice = result as NeedsUserChoice;
      expect(choice.exif, _base);
      expect(choice.device, device);
      expect(choice.distanceKm, greaterThan(kLocationConflictThresholdKm));
    });

    test('uses EXIF when the device has no fix', () {
      final result = resolveSightingLocation(exif: _base, device: null);
      expect((result as UseLocation).source, LocationSource.exif);
    });

    test('falls back to the device when the photo has no GPS', () {
      final result = resolveSightingLocation(exif: null, device: _base);
      final use = result as UseLocation;
      expect(use.source, LocationSource.device);
      expect(use.position, _base);
    });

    test('reports nothing usable when neither source has a location', () {
      expect(
        resolveSightingLocation(exif: null, device: null),
        isA<NoLocation>(),
      );
    });

    test('carries the capture time into the conflict prompt', () {
      final taken = DateTime(2026, 3, 14, 9, 30);
      final result = resolveSightingLocation(
        exif: _base,
        device: _eastOf(_base, 5000),
        takenAt: taken,
      );
      expect((result as NeedsUserChoice).takenAt, taken);
    });

    group('at the threshold boundary', () {
      test('just inside stays silent', () {
        final result = resolveSightingLocation(
          exif: _base,
          device: _eastOf(_base, 240),
        );
        expect(result, isA<UseLocation>());
      });

      test('just outside prompts', () {
        final result = resolveSightingLocation(
          exif: _base,
          device: _eastOf(_base, 260),
        );
        expect(result, isA<NeedsUserChoice>());
      });
    });
  });

  group('isStalePhoto', () {
    final now = DateTime(2026, 9, 9, 12);

    test('a photo with no capture time is never stale', () {
      expect(isStalePhoto(null, now: now), isFalse);
    });

    test('a photo from today is not stale', () {
      expect(isStalePhoto(now.subtract(const Duration(hours: 3)), now: now),
          isFalse);
    });

    test('a photo just under the window is not stale', () {
      expect(
        isStalePhoto(now.subtract(const Duration(days: 6)), now: now),
        isFalse,
      );
    });

    test('a photo at the window is stale', () {
      expect(
        isStalePhoto(
          now.subtract(const Duration(days: kStalePhotoWarningDays)),
          now: now,
        ),
        isTrue,
      );
    });

    test('a months-old photo is stale', () {
      expect(isStalePhoto(DateTime(2026, 5, 1), now: now), isTrue);
    });
  });

  group('LocationSource wire values', () {
    test('match the backend enum', () {
      expect(LocationSource.exif.wireValue, 'EXIF');
      expect(LocationSource.device.wireValue, 'DEVICE');
    });
  });
}
