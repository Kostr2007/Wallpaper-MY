{ lib, python3Packages }:

python3Packages.buildPythonApplication {
  pname = "wallpaper-my";
  inherit ((builtins.fromTOML (builtins.readFile ./pyproject.toml)).project) version;
  src = lib.fileset.toSource {
    root = ./.;
    fileset = lib.fileset.unions [
      ./pyproject.toml
      ./src
    ];
  };
  pyproject = true;
  build-system = [ python3Packages.setuptools ];
  dependencies = with python3Packages; [
    numpy
    pillow
  ];
  pythonImportsCheck = [ "wallpaper_my.cli" ];

  meta = {
    description = "Procedural live wallpapers inspired by Android and Material You";
    homepage = "https://github.com/Kostr2007/Wallpaper-MY";
    mainProgram = "wallpaper-my";
    platforms = lib.platforms.linux;
  };
}
