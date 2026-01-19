import os

frontend_dir = r"c:\Users\tindi\Tindi Tech\frontend"

replacements = {
    # CSS
    'href="css pracs.css"': 'href="assets/css/style.css"',
    'href="css%20pracs.css"': 'href="assets/css/style.css"',
    # JS
    'src="javascript pracs.js"': 'src="assets/js/main.js"',
    'src="javascript%20pracs.js"': 'src="assets/js/main.js"',
    # Images (Prevent double replacement if already correct)
    'src="img/': 'src="assets/img/',
    'src="assets/assets/img/': 'src="assets/img/', # Fix double paste safety
    'href="img/': 'href="assets/img/',
    
    # Specific fix for login.html background if inline
    "url('img/": "url('assets/img/",
    'url("img/': 'url("assets/img/',
}

for filename in os.listdir(frontend_dir):
    if filename.endswith(".html"):
        filepath = os.path.join(frontend_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        new_content = content
        for old, new in replacements.items():
            new_content = new_content.replace(old, new)
            
        # Safety check for already migrated paths (don't duplicate assets/assets)
        new_content = new_content.replace('assets/assets/', 'assets/')

        if new_content != content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Fixed: {filename}")
        else:
            print(f"No changes: {filename}")
