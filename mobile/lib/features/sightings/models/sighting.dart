class Sighting {
  final String id;
  final String imagePath;
  final double latitude;
  final double longitude;
  final String? speciesDetected;
  /// Where the coordinates came from: 'EXIF' or 'DEVICE'. Null when the
  /// server predates the field.
  final String? locationSource;
  /// When the photo was taken, if its metadata said so.
  final DateTime? takenAt;
  final DateTime createdAt;

  const Sighting({
    required this.id,
    required this.imagePath,
    required this.latitude,
    required this.longitude,
    this.speciesDetected,
    this.locationSource,
    this.takenAt,
    required this.createdAt,
  });

  factory Sighting.fromJson(Map<String, dynamic> json) => Sighting(
        id: json['id'] as String,
        imagePath: json['image_path'] as String,
        latitude: (json['latitude'] as num).toDouble(),
        longitude: (json['longitude'] as num).toDouble(),
        speciesDetected: json['species_detected'] as String?,
        locationSource: json['location_source'] as String?,
        takenAt: json['taken_at'] == null
            ? null
            : DateTime.parse(json['taken_at'] as String),
        createdAt: DateTime.parse(json['created_at'] as String),
      );
}
