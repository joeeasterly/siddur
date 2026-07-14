import json
import os
import string
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
        local_page = doc.get("local_page")
        if local_page is None:
            continue

        base_name = str(local_page)
        json_path = os.path.join(mt_dir, f"{base_name}.json")
        tex_path = os.path.join(mt_dir, f"{base_name}.tex")

        # Coerce the MongoDB ObjectId to a string so json.dump survives the encounter
        doc['_id'] = str(doc['_id'])

        # 1. Write the sidecar .json file IF AND ONLY IF it doesn't exist
        if not os.path.exists(json_path):
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)

        # 2. Write the corresponding .tex file IF AND ONLY IF it doesn't exist
        if not os.path.exists(tex_path):
            tex_content = generate_tex_content(doc)
            with open(tex_path, 'w', encoding='utf-8') as f:
                f.write(tex_content)

        processed_count += 1

    print(f"Operation complete. Swept {processed_count} valid documents into the 'mt' folder.")

if __name__ == "__main__":
    main()
