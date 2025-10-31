import shutil
import os
from pathlib import Path
from typing import Union


class FileHandler:
    def __init__(self) -> None:
        pass

    def copy_file(self, src: Union[str, Path], dst: Union[str, Path], overwrite: bool = False) -> None:
        src_path = Path(src)
        dst_path = Path(dst)
        if not src_path.is_file():
            raise FileNotFoundError(f"Source file '{src}' does not exist.")
        if dst_path.exists() and not overwrite:
            raise FileExistsError(f"Destination '{dst}' already exists. Use overwrite=True to overwrite.")
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src_path), str(dst_path))

    def move_file(self, src: Union[str, Path], dst: Union[str, Path], overwrite: bool = False) -> None:
        src_path = Path(src)
        dst_path = Path(dst)
        if not src_path.is_file():
            raise FileNotFoundError(f"Source file '{src}' does not exist.")
        if dst_path.exists():
            if overwrite:
                if dst_path.is_file():
                    dst_path.unlink()
                elif dst_path.is_dir():
                    shutil.rmtree(str(dst_path))
            else:
                raise FileExistsError(f"Destination '{dst}' already exists. Use overwrite=True to overwrite.")
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_path), str(dst_path))

    def delete_file(self, path: Union[str, Path]) -> None:
        path_obj = Path(path)
        if path_obj.is_file():
            path_obj.unlink()
        else:
            raise FileNotFoundError(f"File '{path}' does not exist.")

    def create_directory(self, path: Union[str, Path], exist_ok: bool = True) -> None:
        path_obj = Path(path)
        path_obj.mkdir(parents=True, exist_ok=exist_ok)

    def move_directory(self, src: Union[str, Path], dst: Union[str, Path], overwrite: bool = False) -> None:
        src_path = Path(src)
        dst_path = Path(dst)
        if not src_path.is_dir():
            raise FileNotFoundError(f"Source directory '{src}' does not exist.")
        if dst_path.exists():
            if overwrite:
                if dst_path.is_dir():
                    shutil.rmtree(str(dst_path))
                else:
                    dst_path.unlink()
            else:
                raise FileExistsError(f"Destination '{dst}' already exists. Use overwrite=True to overwrite.")
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_path), str(dst_path))

    def delete_directory(self, path: Union[str, Path]) -> None:
        path_obj = Path(path)
        if path_obj.is_dir():
            shutil.rmtree(str(path_obj))
        else:
            raise FileNotFoundError(f"Directory '{path}' does not exist.")


def main() -> None:
    import tempfile
    import sys

    print("Creating FileHandler...")
    handler = FileHandler()

    # Create temp directories for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir) / "test_dir"
        move_dir = Path(tmpdir) / "moved_dir"
        file1 = test_dir / "file1.txt"
        file2 = test_dir / "file2.txt"
        copied_file = test_dir / "copied_file.txt"

        print(f"Creating directory: {test_dir}")
        handler.create_directory(test_dir)

        print(f"Creating file: {file1}")
        file1.write_text("Hello, World!")

        print(f"Copying {file1} to {copied_file}")
        handler.copy_file(file1, copied_file)

        print(f"Moving {copied_file} to {file2}")
        handler.move_file(copied_file, file2)

        try:
            print(f"Deleting file: {file2}")
            handler.delete_file(file2)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)

        print(f"Creating nested directory: {test_dir / 'nested1' / 'nested2'}")
        handler.create_directory(test_dir / "nested1" / "nested2")

        print(f"Moving directory {test_dir} to {move_dir}")
        handler.move_directory(test_dir, move_dir)

        print(f"Deleting moved directory: {move_dir}")
        handler.delete_directory(move_dir)

        print("All tests completed successfully.")


if __name__ == "__main__":
    main()