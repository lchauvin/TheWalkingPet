import 'dart:io';

import 'package:exif/exif.dart';
import 'package:flutter/foundation.dart';
import 'package:permission_handler/permission_handler.dart';

import 'location_resolution.dart';

/// Ask for the access that lets a picked photo keep its GPS tags.
///
/// Android redacts GPS from gallery images unless the app holds
/// ACCESS_MEDIA_LOCATION. Declaring it in the manifest is not enough — it is a
/// runtime grant. The picker itself needs no library-wide read permission,
/// since choosing a file grants access to that one file, so this asks for
/// nothing broader.
///
/// Returns whether the grant was obtained. A refusal is not fatal: the photo
/// simply reads as having no location and the device fix is used instead.
Future<bool> ensureMediaLocationAccess() async {
  if (!Platform.isAndroid) return true;

  try {
    var status = await Permission.accessMediaLocation.status;
    if (!status.isGranted) {
      status = await Permission.accessMediaLocation.request();
    }

    _log('accessMediaLocation=$status');
    return status.isGranted;
  } catch (e) {
    _log('permission request failed: $e');
    return false;
  }
}

/// What a picked photo can tell us about itself.
class PhotoMetadata {
  final LatLng? position;
  final DateTime? takenAt;

  const PhotoMetadata({this.position, this.takenAt});

  static const empty = PhotoMetadata();
}

/// Read GPS and capture time out of a photo's EXIF block.
///
/// Never throws: a photo whose metadata cannot be read is not an error, it just
/// means the device location is the only thing left to go on. Callers treat an
/// empty result and a missing tag the same way.
Future<PhotoMetadata> readPhotoMetadata(File image) async {
  try {
    final tags = await readExifFromBytes(await image.readAsBytes());
    if (tags.isEmpty) {
      _log('no EXIF at all');
      return PhotoMetadata.empty;
    }

    final metadata = PhotoMetadata(
      position: _readGps(tags),
      takenAt: _readTakenAt(tags),
    );
    // Whether GPS survives the picker is platform- and permission-dependent
    // (Android redacts it without ACCESS_MEDIA_LOCATION), so say plainly which
    // of the two tags came back rather than leaving a silent fallback to guess at.
    _log('${tags.length} tags, gps=${metadata.position ?? "none"}, '
        'taken=${metadata.takenAt ?? "none"}');
    return metadata;
  } catch (e) {
    _log('unreadable: $e');
    return PhotoMetadata.empty;
  }
}

void _log(String message) {
  if (kDebugMode) debugPrint('[PhotoMetadata] $message');
}

LatLng? _readGps(Map<String, IfdTag> tags) {
  final lat = _toDegrees(tags['GPS GPSLatitude']);
  final lon = _toDegrees(tags['GPS GPSLongitude']);
  if (lat == null || lon == null) return null;

  // Ref tells us which hemisphere; without it the coordinates land mirrored
  // across the equator or the prime meridian.
  final latRef = tags['GPS GPSLatitudeRef']?.printable.trim().toUpperCase();
  final lonRef = tags['GPS GPSLongitudeRef']?.printable.trim().toUpperCase();

  final signedLat = latRef == 'S' ? -lat : lat;
  final signedLon = lonRef == 'W' ? -lon : lon;

  if (signedLat.abs() > 90 || signedLon.abs() > 180) return null;
  // Exactly (0, 0) is Null Island — far more often an unset tag than a real fix.
  if (signedLat == 0 && signedLon == 0) return null;

  return LatLng(signedLat, signedLon);
}

/// EXIF stores GPS as three rationals: degrees, minutes, seconds.
double? _toDegrees(IfdTag? tag) {
  final values = tag?.values.toList();
  if (values == null || values.length < 3) return null;

  final parts = <double>[];
  for (final value in values.take(3)) {
    if (value is! Ratio) return null;
    if (value.denominator == 0) return null;
    parts.add(value.numerator / value.denominator);
  }
  return parts[0] + parts[1] / 60.0 + parts[2] / 3600.0;
}

/// `DateTimeOriginal` is written as `YYYY:MM:DD HH:MM:SS` and carries no zone,
/// so it is read as local time — the same clock the reporter is looking at.
DateTime? _readTakenAt(Map<String, IfdTag> tags) {
  final raw = (tags['EXIF DateTimeOriginal'] ?? tags['Image DateTime'])
      ?.printable
      .trim();
  if (raw == null || raw.isEmpty) return null;

  final match = RegExp(r'^(\d{4}):(\d{2}):(\d{2})[ T](\d{2}):(\d{2}):(\d{2})')
      .firstMatch(raw);
  if (match == null) return null;

  int group(int i) => int.parse(match.group(i)!);
  try {
    return DateTime(
      group(1),
      group(2),
      group(3),
      group(4),
      group(5),
      group(6),
    );
  } catch (_) {
    return null;
  }
}
