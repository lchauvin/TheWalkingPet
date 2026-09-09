class PetImage {
  final String id;
  final String imagePath;
  final bool isPrimary;

  const PetImage({
    required this.id,
    required this.imagePath,
    required this.isPrimary,
  });

  factory PetImage.fromJson(Map<String, dynamic> json) => PetImage(
        id: json['id'] as String,
        imagePath: json['image_path'] as String,
        isPrimary: json['is_primary'] as bool? ?? false,
      );
}

class Pet {
  final String id;
  final String name;
  final String species;
  final String? breed;
  final String? description;
  final bool isMicrochipped;
  final List<PetImage> images;

  const Pet({
    required this.id,
    required this.name,
    required this.species,
    this.breed,
    this.description,
    required this.isMicrochipped,
    required this.images,
  });

  factory Pet.fromJson(Map<String, dynamic> json) => Pet(
        id: json['id'] as String,
        name: json['name'] as String,
        species: json['species'] as String,
        breed: json['breed'] as String?,
        description: json['description'] as String?,
        isMicrochipped: json['is_microchipped'] as bool? ?? false,
        images: (json['images'] as List<dynamic>? ?? [])
            .map((e) => PetImage.fromJson(e as Map<String, dynamic>))
            .toList(),
      );

  String? get primaryImagePath {
    if (images.isEmpty) return null;
    return images.firstWhere(
      (i) => i.isPrimary,
      orElse: () => images.first,
    ).imagePath;
  }
}
