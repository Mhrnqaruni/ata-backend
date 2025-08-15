#!/usr/bin/env python3
import os

# ─── CONFIGURE ────────────────────────────────────────────────────────────────
skip_dirs = [
    "venv",
    ".pytest_cache",
    "node_modules",
    ".git"
    # add more folder names here to skip
]

output_file = "directory_map.txt"
# ────────────────────────────────────────────────────────────────────────────────

def main():
    root_dir = os.getcwd()
    base = os.path.basename(root_dir.rstrip(os.path.sep))
    entries = []

    with open(output_file, "w", encoding="utf-8") as f:
        # Print the root itself
        f.write(f"/{base}\n")

        for current_root, dirs, files in os.walk(root_dir):
            rel = os.path.relpath(current_root, root_dir)
            # build prefix like "/base" or "/base/sub/dir"
            if rel == ".":
                prefix = f"/{base}"
            else:
                prefix = f"/{base}/{rel.replace(os.path.sep, '/')}"
                # write this folder’s path
                f.write(prefix + "/\n")

            # handle and prune skip_dirs
            for d in list(dirs):
                if d in skip_dirs:
                    skip_path = prefix + "/" + d + "/"
                    f.write(skip_path + " (too much files)\n")
                    dirs.remove(d)  # prevents os.walk from entering it

            # list files
            for filename in files:
                f.write(prefix + "/" + filename + "\n")

    print(f"Directory map written to {output_file}")

if __name__ == "__main__":
    main()
