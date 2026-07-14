import json
import sys
import os
import string
import subprocess
import shutil

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
    """Generates sequential macro identifiers (\\blockA, \\blockB, etc.)."""
    if index < 26:
        return f"\\block{string.ascii_uppercase[index]}"
    else:
        return f"\\block{string.ascii_uppercase[(index // 26) - 1]}{string.ascii_uppercase[index % 26]}"

def generate_tex_content(data):
    page_label = data.get('page_label', 'Unknown')
    annotations = data.get('annotations', [])

    tex_lines = [
        r"% ==========================================",
        r"% AUTO-GENERATED STAGING FILE FOR PAGE " + page_label,
        r"% ==========================================",
        r"\documentclass[14pt]{extarticle}",
        r"\usepackage[paperwidth=5.5in, paperheight=8.5in, margin=0.6in]{geometry}",
        r"\usepackage{polyglossia}",
        r"\setdefaultlanguage{english}",
        r"\setotherlanguage{hebrew}",
        r"\newfontfamily\hebrewfont[Script=Hebrew]{Ezra SIL} % Update your local system font here",
        "",
        r"% Custom page numbering to yield " + page_label + r".a, " + page_label + r".b, etc.",
        r"\renewcommand{\thepage}{" + page_label + r".\alph{page}}",
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

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python siddur_pipeline.py <input.json>")
        sys.exit(1)
        
    json_path = os.path.abspath(sys.argv[1])
    if not os.path.exists(json_path):
        print(f"File not found: {json_path}")
        sys.exit(1)
        
    folder = os.path.dirname(json_path)
    basename = os.path.splitext(os.path.basename(json_path))[0]
    tex_path = os.path.join(folder, f"{basename}.tex")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    tex_content = generate_tex_content(data)
    
    # Write sidecar .tex file right next to the original .json
    with open(tex_path, 'w', encoding='utf-8') as f:
        f.write(tex_content)
    print(f"Successfully generated: {tex_path}")
    
    # Compilation workflow
    tmp_dir = "/tmp/latex_build"
    os.makedirs(tmp_dir, exist_ok=True)
    
    print(f"Compiling {tex_path} via xelatex...")
    try:
        # polyglossia + RTL strings require xelatex (or lualatex)
        result = subprocess.run([
            "xelatex",
            "-interaction=nonstopmode",
            f"-output-directory={tmp_dir}",
            tex_path
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        generated_pdf = os.path.join(tmp_dir, f"{basename}.pdf")
        target_pdf = "/tmp/test.pdf"
        
        if os.path.exists(generated_pdf):
            shutil.move(generated_pdf, target_pdf)
            print(f"Compilation success! Target output moved to: {target_pdf}")
        else:
            print("ERROR: xelatex ran but the expected PDF was not generated.")
            print("Tail-end of compilation log:")
            print("\n".join(result.stdout.splitlines()[-20:]))
            
    except FileNotFoundError:
        print("ERROR: 'xelatex' binary not found. Verify it is inside your shell's $PATH.")
        sys.exit(1)
