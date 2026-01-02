import os

class DirScanner:
    def __init__(self, root_path: str):
        self._root = root_path
        self._tree = {}


    def tree(self) -> dict:
        SKIP_DIRS = {
            ".git",
            "node_modules",
            ".venv",
            "venv",
            "__pycache__",
            "dist",
            "build",
            "out",
            "coverage",
            ".cache",
            ".idea",
            ".vscode",
        }

        for current_root, dirs, files in os.walk(self._root):
            # IMPORTANT: mutate dirs in place to stop recursion
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

            self._tree[current_root] = {
                "dirs": dirs,
                "files": files
            }

        return self._tree
    
    #reads a file and returns its data 
    def file_contents(self, relative_path: str) -> str:
        full_path = os.path.join(self._root, relative_path)

        if not os.path.isfile(full_path):
            raise FileNotFoundError(f"Not a file: {relative_path}")

        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            contents = f.read()

        return contents

    

        


        
    


