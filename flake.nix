
{
  description = "Python environment with Markdown and WeasyPrint";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };

      python = pkgs.python312.withPackages (ps: with ps; [
        markdown
        weasyprint
      ]);

    in {
      devShells.${system}.default = pkgs.mkShell {
        packages = [
          python
          pkgs.gobject-introspection
          pkgs.pango
          pkgs.glib
          pkgs.cairo
          pkgs.gdk-pixbuf
          pkgs.fontconfig
          pkgs.freetype
        ];

        shellHook = ''
          echo "Python Markdown + WeasyPrint environment"
          python --version
        '';
      };
    };
}
