import json
import os
import string
import re
import math
from pymongo import MongoClient

def escape_latex(text):
    """Sanitizes text so LaTeX doesn't choke and die on a stray ampersand."""
    escaped = text.replace('\\', r'\textbackslash{}') \
                  .replace('&', r'\&') \
                  .replace('%', r'\%') \
                  .replace('$', r'\$') \
                  .replace('#', r'\#') \
                  .replace('_', r'\_') \
                  .replace('{', r'\{') \
                  .replace('}', r'\}')
    return escaped.replace('\n', ' \\\\\n')

def get_macro_name(index):
    """Generates sequential macro identifiers (\blockA, \blockB, etc.)."""
    if index < 26:
        return f"\\block{string.ascii_uppercase[index]}"
    else:
        return f"\\block{string.ascii_uppercase[(index // 26) - 1]}{string.ascii_uppercase[index % 26]}"

def generate_tex_content(data):
    page_label = data.get('page_label', 'Unknown')
    annotations = data.get('annotations', [])

    tex_lines = [
        r"% ==========================================",
        r"% AUTO-GENERATED STAGING FILE FOR PAGE " + str(page_label),
        r"% ==========================================",
        r"\documentclass{siddur}",
        "",
        r"% Custom page numbering to yield " + str(page_label) + r".a, " + str(page_label) + r".b, etc.",
        r"\renewcommand{\thepage}{" + str(page_label) + r".\alph{page}}",
        "",
        r"% --- MACRO DEFINITIONS ---"
    ]

    macro_calls = []
    for i, anno in enumerate(annotations):
        macro_name = get_macro_name(i)
        macro_calls.append(macro_name)

        body = anno.get('body', [{}])[0]
        text_content = escape_latex(body.get('value', ''))
        lang = body.get('language', 'en')

        tex_lines.append(rf"\newcommand{{{macro_name}}}{{%")
        if lang == 'he':
            tex_lines.append(r"  \begin{hebrew}")
            tex_lines.append(f"  {text_content}")
            tex_lines.append(r"  \end{hebrew}%")
        else:
            tex_lines.append(f"  {text_content}%")
        tex_lines.append(r"}")
        tex_lines.append("")

    tex_lines.append(r"% --- DOCUMENT BODY ---")
    tex_lines.append(r"\begin{document}")

    for call in macro_calls:
        tex_lines.append(call)
        tex_lines.append(r"\vspace{1em}")
        tex_lines.append(r"% \newpage % Uncomment to break page here")
        tex_lines.append("")

    tex_lines.append(r"\end{document}")
    return "\n".join(tex_lines)

def main():
    mongo_uri = os.environ.get("MONGO_URI")
    if not mongo_uri:
        raise ValueError("The MONGO_URI environment variable is missing. I'm not clairvoyant.")

    client = MongoClient(mongo_uri)
    db = client.get_database("docs")
    collection = db.get_collection("mishkan")

    # Set up the target directory relative to where the script is executed
    mt_dir = os.path.join(os.getcwd(), "mt")
    os.makedirs(mt_dir, exist_ok=True)

    # Query: Documents where 'annotations' exists, is an array, and is not empty.
    query = {
        "annotations": {
            "$exists": True,
            "$type": "array",
            "$not": {"$size": 0}
        }
    }

    cursor = collection.find(query)
    processed_count = 0

    for doc in cursor:
        page_label = doc.get("page_label")
        if not page_label:
            continue

        # Sanitize any rogue slashes so the OS doesn't try to make subdirectories
        base_name = str(page_label).replace('/', '_')
        json_path = os.path.join(mt_dir, f"{base_name}.json")
        tex_path = os.path.join(mt_dir, f"{base_name}.tex")

        # Coerce the MongoDB ObjectId to a string so json.dump survives the encounter
        doc_id = str(doc['_id'])
        doc['_id'] = doc_id

        # 1. Inject the public viewer URL (using page_label so the router actually finds it)
        doc['page_url'] = f"https://momoiro.hallyu.io/mishkan/{page_label}"

        # 2. Inject IIIF bounding box URLs into every annotation
        for anno in doc.get("annotations", []):
            selector = anno.get("target", {}).get("selector", {})
            val = selector.get("value", "")
            
            x, y, w, h = 0, 0, 0, 0
            valid_box = False
            
            if selector.get("type") == "FragmentSelector":
                match = re.search(r'xywh=(?:pixel:)?(-?[\d.]+),(-?[\d.]+),(-?[\d.]+),(-?[\d.]+)', val)
                if match:
                    # Replicating Math.floor() from your app.js
                    x, y, w, h = [math.floor(float(v)) for v in match.groups()]
                    valid_box = True
                    
            elif selector.get("type") == "SvgSelector":
                match = re.search(r'points="([^"]+)"', val)
                if match:
                    pts = [float(p) for p in re.split(r'[\s,]+', match.group(1).strip()) if p]
                    xs, ys = pts[0::2], pts[1::2]
                    x, y = math.floor(min(xs)), math.floor(min(ys))
                    w, h = math.floor(max(xs) - x), math.floor(max(ys) - y)
                    valid_box = True
                    
            if valid_box:
                # Using the proxied public URL instead of the internal Docker hostname
                # so the links are actually clickable from the exported JSON.
                anno["image_url"] = f"https://momoiro.hallyu.io/mishkan/iiif/3/mishkan%2F{doc_id}.jp2/{x},{y},{w},{h}/max/0/default.jpg"

        # 3. Write the sidecar .json file IF AND ONLY IF it doesn't exist
        if not os.path.exists(json_path):
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)

        # 4. Write the corresponding .tex file IF AND ONLY IF it doesn't exist
        if not os.path.exists(tex_path):
            tex_content = generate_tex_content(doc)
            with open(tex_path, 'w', encoding='utf-8') as f:
                f.write(tex_content)

        processed_count += 1

    print(f"Operation complete. Swept {processed_count} valid documents into the 'mt' folder.")

if __name__ == "__main__":
    main()
