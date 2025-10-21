{
  description = "For Ausbildung Email sender";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
    nixpkgs-python.url = "github:cachix/nixpkgs-python";
  };

  outputs = { self, nixpkgs, nixpkgs-python }:
  let
    pkgs = nixpkgs.legacyPackages.x86_64-linux;
    pythonPackages = pkgs.python310Packages;
  in
  {

    devShells.x86_64-linux.default = pkgs.mkShell {

      NIX_LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
        pkgs.stdenv.cc.cc
        pkgs.zlib
        # pkgs.openblas
      ];
      NIX_LD = pkgs.lib.fileContents "${pkgs.stdenv.cc}/nix-support/dynamic-linker";
      buildInputs = with pkgs; [
        pythonPackages.python
        pythonPackages.pip
        gcc
        # pythonPackages.cython
        # gfortran
        # openblas
        pkg-config
        mariadb-connector-c
        # zlib
      ];
      shellHook = ''
        export LD_LIBRARY_PATH=$NIX_LD_LIBRARY_PATH

        folder_path="venv"

        if [ ! -d "$folder_path" ]; then
          echo "Creating virtual env: $folder_path"
          python -m venv venv
          
          # Activate venv to install build tools
          source venv/bin/activate
          
          # echo "Downgrading setuptools..."
          # pip install "setuptools<58"
          
          # --- THIS IS THE FIX ---
          # echo "Installing wheel package..."
          # pip install wheel
          # --- END OF FIX ---
          
          # deactivate

        else
          echo "Virtual env '$folder_path' already exists."
        fi

        source venv/bin/activate
      '';
    };

  };
}
