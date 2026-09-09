class LostDeclaration {
  final String id;
  final String petId;
  final double lastSeenLat;
  final double lastSeenLon;
  final double searchRadiusKm;
  final double? rewardAmount;
  final String status;
  final String? description;
  final DateTime createdAt;

  const LostDeclaration({
    required this.id,
    required this.petId,
    required this.lastSeenLat,
    required this.lastSeenLon,
    required this.searchRadiusKm,
    this.rewardAmount,
    required this.status,
    this.description,
    required this.createdAt,
  });

  factory LostDeclaration.fromJson(Map<String, dynamic> json) => LostDeclaration(
        id: json['id'] as String,
        petId: json['pet_id'] as String,
        lastSeenLat: (json['last_seen_lat'] as num).toDouble(),
        lastSeenLon: (json['last_seen_lon'] as num).toDouble(),
        searchRadiusKm: (json['search_radius_km'] as num).toDouble(),
        rewardAmount: json['reward_amount'] != null
            ? (json['reward_amount'] as num).toDouble()
            : null,
        status: json['status'] as String,
        description: json['description'] as String?,
        createdAt: DateTime.parse(json['created_at'] as String),
      );

  bool get isActive => status == 'ACTIVE';
}
