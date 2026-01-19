
import os
import shutil
import re

FRONTEND = r"c:\Users\tindi\Tindi Tech\frontend"
ASSETS_IMG = os.path.join(FRONTEND, "assets", "img")
ASSETS_CSS = os.path.join(FRONTEND, "assets", "css")
ASSETS_JS = os.path.join(FRONTEND, "assets", "js")

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

ensure_dir(ASSETS_IMG)
ensure_dir(ASSETS_CSS)
ensure_dir(ASSETS_JS)

# 1. Move Files & Folders
moves = [
    # (Source Path in Frontend, Dest Folder, New Name or None)
    ("css pracs.css", ASSETS_CSS, "style.css"),
    ("syle.css.css", ASSETS_CSS, "style_backup.css"),
    ("Tindi Tech 2.png", ASSETS_IMG, "logo.png"),
    ("site-api.js", ASSETS_JS, None),
    ("javascript pracs.js", ASSETS_JS, "main.js"),
    ("server.js", r"c:\Users\tindi\Tindi Tech\backend\reference", "server_node.js"),
]

# Move individual files
for src_name, dest_dir, rename in moves:
    src_path = os.path.join(FRONTEND, src_name)
    if os.path.exists(src_path):
        dest_name = rename if rename else src_name
        dest_path = os.path.join(dest_dir, dest_name)
        try:
            shutil.move(src_path, dest_path)
            print(f"Moved {src_name} -> {dest_path}")
        except Exception as e:
            print(f"Error moving {src_name}: {e}")

# Move directories (merge)
def move_dir_contents(src_dir_name, dest_dir):
    src_dir = os.path.join(FRONTEND, src_dir_name)
    if os.path.exists(src_dir):
        for item in os.listdir(src_dir):
            s = os.path.join(src_dir, item)
            d = os.path.join(dest_dir, item)
            try:
                if os.path.exists(d):
                    os.remove(d) # Overwrite if exists, or skip?
                shutil.move(s, d)
                print(f"Moved {src_dir_name}/{item} -> {d}")
            except Exception as e:
                print(f"Error moving {item}: {e}")
        try:
            os.rmdir(src_dir)
            print(f"Removed {src_dir}")
        except:
            pass

move_dir_contents("img", ASSETS_IMG)
move_dir_contents("js", ASSETS_JS)

# 2. Update HTML
replacements = [
    ('href="css pracs.css"', 'href="assets/css/style.css"'),
    ('src="Tindi Tech 2.png"', 'src="assets/img/logo.png"'),
    ('src="img/', 'src="assets/img/'),
    ('src="js/', 'src="assets/js/'),
    ('src="site-api.js"', 'src="assets/js/site-api.js"'),
    ('src="javascript pracs.js"', 'src="assets/js/main.js"'),
]

for filename in os.listdir(FRONTEND):
    if filename.endswith(".html"):
        filepath = os.path.join(FRONTEND, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        new_content = content
        for old, new in replacements:
            new_content = new_content.replace(old, new)
        
        if content != new_content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Updated {filename}")

