class Panel {
  final int ymin;
  final int xmin;
  final int ymax;
  final int xmax;

  Panel({
    required this.ymin,
    required this.xmin,
    required this.ymax,
    required this.xmax,
  });

  factory Panel.fromJson(Map<String, dynamic> json) {
    return Panel(
      ymin: json['ymin'] as int,
      xmin: json['xmin'] as int,
      ymax: json['ymax'] as int,
      xmax: json['xmax'] as int,
    );
  }

  Map<String, dynamic> toJson() {
    return {'ymin': ymin, 'xmin': xmin, 'ymax': ymax, 'xmax': xmax};
  }
}

class ComicPageSegmentation {
  final List<Panel> panels;

  ComicPageSegmentation({required this.panels});

  factory ComicPageSegmentation.fromJson(Map<String, dynamic> json) {
    return ComicPageSegmentation(
      panels: (json['panels'] as List<dynamic>)
          .map((e) => Panel.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() {
    return {'panels': panels.map((e) => e.toJson()).toList()};
  }
}
