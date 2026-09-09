class PetMatch {
  final String id;
  final String sightingId;
  final String lostDeclarationId;
  final double similarityScore;
  final String status;
  final DateTime createdAt;

  // Only available after confirming
  final double? sightingLat;
  final double? sightingLon;
  final String? sightingImagePath;

  const PetMatch({
    required this.id,
    required this.sightingId,
    required this.lostDeclarationId,
    required this.similarityScore,
    required this.status,
    required this.createdAt,
    this.sightingLat,
    this.sightingLon,
    this.sightingImagePath,
  });

  factory PetMatch.fromJson(Map<String, dynamic> json) => PetMatch(
        id: json['id'] as String,
        sightingId: json['sighting_id'] as String,
        lostDeclarationId: json['lost_declaration_id'] as String,
        similarityScore: (json['similarity_score'] as num).toDouble(),
        status: json['status'] as String,
        createdAt: DateTime.parse(json['created_at'] as String),
        sightingLat: json['sighting_lat'] != null
            ? (json['sighting_lat'] as num).toDouble()
            : null,
        sightingLon: json['sighting_lon'] != null
            ? (json['sighting_lon'] as num).toDouble()
            : null,
        sightingImagePath: json['sighting_image_path'] as String?,

      );

  bool get isPending => status == 'PENDING';
  bool get isConfirmed => status == 'CONFIRMED';
  bool get isRejected => status == 'REJECTED';
}
