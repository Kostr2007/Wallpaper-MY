{
  description = "Procedural live wallpapers for Material You and i3";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { self, nixpkgs }:
    let
      forSystems = nixpkgs.lib.genAttrs [
        "x86_64-linux"
        "aarch64-linux"
      ];
    in
    {
      lib.mkGallery =
        {
          pkgs,
          width ? 3840,
          height ? 1440,
        }:
        pkgs.runCommand "wallpaper-my-gallery-${toString width}x${toString height}"
          { nativeBuildInputs = [ (pkgs.buildPackages.callPackage ./package.nix { }) ]; }
          ''
            wallpaper-my --output "$out" --width ${toString width} --height ${toString height}
          '';

      packages = forSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          default = pkgs.callPackage ./package.nix { };
          gallery = self.lib.mkGallery { inherit pkgs; };
        }
      );

      checks = forSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          generator =
            pkgs.runCommand "wallpaper-my-tests"
              {
                nativeBuildInputs = [
                  self.packages.${system}.default
                  (pkgs.python3.withPackages (ps: [ ps.pillow ]))
                ];
              }
              ''
                python ${./tests/generator.py} ${./src}
                touch "$out"
              '';
        }
      );
    };
}
