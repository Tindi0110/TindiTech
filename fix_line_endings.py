with open('build.sh', 'rb') as f:
    content = f.read()

# Replace CRLF with LF
clean_content = content.replace(b'\r\n', b'\n')

with open('build.sh', 'wb') as f:
    f.write(clean_content)

print("Fixed line endings for build.sh")
