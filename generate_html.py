import markdown
import sys
import re

with open("/home/jk/.gemini/antigravity/brain/0ec9fc8e-e2c9-4ca2-9f9d-61dfca61ec7c/dvcon_abstract.md", "r") as f:
    text = f.read()

# Replace mermaid blocks with div class="mermaid"
text = re.sub(r'```mermaid\n(.*?)\n```', r'<div class="mermaid">\1</div>', text, flags=re.DOTALL)

html_content = markdown.markdown(text, extensions=['extra', 'toc'])

html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>DVCon Extended Abstract</title>
<style>
    body {{
        font-family: Arial, sans-serif;
        line-height: 1.6;
        max-width: 800px;
        margin: 0 auto;
        padding: 20px;
        color: #333;
    }}
    h1, h2, h3 {{ color: #2c3e50; }}
    pre {{
        background: #f4f4f4;
        padding: 10px;
        border-radius: 5px;
        overflow-x: auto;
    }}
    code {{
        background: #f4f4f4;
        padding: 2px 4px;
        border-radius: 3px;
        font-family: monospace;
    }}
    .mermaid {{
        text-align: center;
        margin: 20px 0;
    }}
</style>
<script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
    mermaid.initialize({{ startOnLoad: true }});
</script>
</head>
<body>
{html_content}
</body>
</html>"""

with open("dvcon_abstract.html", "w") as f:
    f.write(html)
print("Generated dvcon_abstract.html")
