import os

#writes files
class FileWriter:
    def __init__(self, out_dir: str = "outputs"):
        self.out_dir = out_dir

    def write_md(self, filename: str, content: str) -> str:
        if not filename.endswith(".md"):
            filename += ".md"

        os.makedirs(self.out_dir, exist_ok=True)

        out_path = os.path.join(self.out_dir, filename)
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

        return out_path
