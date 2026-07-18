import json
import os
import string
import re
import math
from xml.sax.saxutils import escape
from pymongo import MongoClient

def escape_xml(text):
    """Sanitizes text so XML parsers don't violently shit the bed."""
    return escape(text, {'"': "&quot;", "'": "&apos;"})

def get_block_id(index):
    """Generates sequential XML IDs (block_A, block_B, etc.) because we aren't savages."""
    if index < 26:
        return f"block_{string.ascii_uppercase[index]}"
    else:
        return f"block_{string.ascii_uppercase[(index // 26) - 1]}{string.ascii_uppercase[index % 26]}"

def generate_tei_content(data):
    page_label = escape_xml(str(data.get('page_label', 'Unknown')))
    annotations = data.get('annotations', [])

    # We declare the TEI namespace, the XInclude namespace, and provide the RNG schemas.
    # This guarantees oXygen validates the file immediately upon opening.
    tei_lines = [
        f'<?xml version="1.0" encoding="UTF-8"?>',
        f'<?xml-model href="http://www.tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng" type="application/xml" schematypens="http://relaxng.org/ns/structure/1.0"?>',
        f'<?xml-model href="http://www.tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng" type="application/xml" schematypens="http://purl.oclc.org/dsdl/schematron"?>',
        f'<TEI xmlns="http://www.tei-c.org/ns/1.0" xmlns:xi="http://www.w3.org/2001/XInclude">',
        f'  <xi:include href="../teiHeader.xml"/>',
        f'  <text>',
        f'    <body>',
        f'      <div type="page" n="{page_label}">',
        f'        <pb n="{page_label}"/>'
    ]

    for i, anno in enumerate(annotations):
        block_id = get_block_id(i)
        body = anno.get('body', [{}])[0]
        
        raw_text = body.get('value', '')
        lang = escape_xml(body.get('language', 'en'))
        facs_url = escape_xml(anno.get('image_url', ''))
        
        facs_attr = f' facs="{facs_url}"' if facs_url else ''

        tei_lines.append(f'        <lg xml:id="{block_id}" xml:lang="{lang}"{facs_attr}>')
        
        # Split text by newline and wrap each segment in an <l> tag
        for line in raw_text.split('\n'):
            if line.strip():  # Ignore empty lines
                tei_lines.append(f'          <l>{escape_xml(line)}</l>')
                
        tei_lines.append(f'        </lg>')

    tei_lines.append(f'      </div>')
    tei_lines.append(f'    </body>')
    tei_lines.append(f'  </text>')
    tei_lines.append(f'</TEI>')
    
    return "\n".join(tei_lines)

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
        xml_path = os.path.join(mt_dir, f"{base_name}.xml")

        # Coerce the MongoDB ObjectId to a string so json.dump survives the encounter
        doc_id = str(doc['_id'])
        doc['_id'] = doc_id

        # 1. Inject the public viewer URL
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
                anno["image_url"] = f"https://momoiro.hallyu.io/mishkan/iiif/3/mishkan%2F{doc_id}.jp2/{x},{y},{w},{h}/max/0/default.jpg"

        # 3. Write the sidecar .json file IF AND ONLY IF it doesn't exist
        if not os.path.exists(json_path):
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)

        # 4. Write the corresponding .xml file IF AND ONLY IF it doesn't exist
        if not os.path.exists(xml_path):
            tei_content = generate_tei_content(doc)
            with open(xml_path, 'w', encoding='utf-8') as f:
                f.write(tei_content)

        processed_count += 1

    print(f"Operation complete. Swept {processed_count} valid XML documents into the 'mt' folder.")

if __name__ == "__main__":
    main()