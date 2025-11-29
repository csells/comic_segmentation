class Panel {
  Panel({
    required this.ymin,
    required this.xmin,
    required this.ymax,
    required this.xmax,
  });

  factory Panel.fromJson(Map<String, dynamic> json) => Panel(
    ymin: json['ymin'] as int,
    xmin: json['xmin'] as int,
    ymax: json['ymax'] as int,
    xmax: json['xmax'] as int,
  );
  final int ymin;
  final int xmin;
  final int ymax;
  final int xmax;

  Map<String, dynamic> toJson() => {
    'ymin': ymin,
    'xmin': xmin,
    'ymax': ymax,
    'xmax': xmax,
  };
}

class ComicPageSegmentation {
  ComicPageSegmentation({required this.panels});

  factory ComicPageSegmentation.fromJson(Map<String, dynamic> json) =>
      ComicPageSegmentation(
        panels: (json['panels'] as List<dynamic>)
            .map((e) => Panel.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
  final List<Panel> panels;

  Map<String, dynamic> toJson() => {
    'panels': panels.map((e) => e.toJson()).toList(),
  };
}
