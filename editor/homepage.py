import re
from .config import HUGO_TOML, HOME_INFO


def read():
    toml = HUGO_TOML.read_text(encoding="utf-8") if HUGO_TOML.exists() else ""
    name = re.search(r'Title\s*=\s*"([^"]*)"', toml)
    bio  = re.search(r'Content\s*=\s*"([^"]*)"', toml)
    name = name.group(1) if name else "Lighton"
    bio  = bio.group(1)  if bio  else ""
    entries = []
    if HOME_INFO.exists():
        html = HOME_INFO.read_text(encoding="utf-8")
        for block in re.finditer(
            r'<div class="cv-entry">(.*?)<span class="cv-period">(.*?)</span>\s*</div>',
            html, re.DOTALL):
            inner = block.group(1)
            s = re.search(r'class="cv-school">(.*?)<', inner)
            d = re.search(r'class="cv-degree">(.*?)<', inner)
            entries.append({"school": s.group(1) if s else "",
                            "degree": d.group(1) if d else "",
                            "period": block.group(2).strip()})
    return {"name": name, "bio": bio, "education": entries}


def write(name, bio, education):
    toml = HUGO_TOML.read_text(encoding="utf-8")
    toml = re.sub(r'(\[params\.homeInfoParams\]\s*\n\s*Title\s*=\s*)"[^"]*"',
                  f'\\1"{name}"', toml)
    toml = re.sub(r'(Content\s*=\s*)"[^"]*"', f'\\1"{bio}"', toml)
    HUGO_TOML.write_text(toml, encoding="utf-8")

    edu_html = ""
    for e in education:
        edu_html += (
            f'\n        <div class="cv-entry">'
            f'\n          <div class="cv-entry-left">'
            f'\n            <span class="cv-school">{e["school"]}</span>'
            f'\n            <span class="cv-degree">{e["degree"]}</span>'
            f'\n          </div>'
            f'\n          <span class="cv-period">{e["period"]}</span>'
            f'\n        </div>'
        )

    parts = [
        '{{- with site.Params.homeInfoParams }}\n',
        '<article class="first-entry home-info">\n',
        '    <header class="entry-header">\n',
        '        <h1>{{ .Title | markdownify }}</h1>\n',
        '    </header>\n',
        '    <div class="entry-content md-content">\n',
        '        {{ $opts := dict "display" "block" }}\n',
        '        {{ .Content | $.Page.RenderString $opts }}\n',
        '    </div>\n\n',
        '    <div class="cv-section">\n',
        '      <h2 class="cv-title">학력</h2>\n',
        f'      <div class="cv-entries">{edu_html}\n      </div>\n',
        '    </div>\n\n',
        '    <footer class="entry-footer">\n',
        '        {{ partial "social_icons.html" (dict "align" site.Params.homeInfoParams.AlignSocialIconsTo) }}\n',
        '    </footer>\n',
        '</article>\n',
        '{{- end -}}\n\n',
        '<style>\n',
        '.cv-section{margin-top:1.2rem;padding-top:1rem;border-top:1px solid var(--border)}\n',
        '.cv-title{font-size:.72rem;font-weight:700;text-transform:uppercase;',
        'letter-spacing:.1em;color:var(--secondary);margin:0 0 .75rem}\n',
        '.cv-entries{display:flex;flex-direction:column;gap:.6rem}\n',
        '.cv-entry{display:flex;align-items:baseline;justify-content:space-between;gap:1rem}\n',
        '.cv-entry-left{display:flex;gap:.5rem;align-items:baseline}\n',
        '.cv-school{font-weight:600;font-size:.9rem}\n',
        '.cv-degree{font-size:.82rem;color:var(--secondary)}\n',
        '.cv-period{font-size:.8rem;color:var(--secondary);white-space:nowrap;flex-shrink:0}\n',
        '</style>\n',
    ]
    HOME_INFO.parent.mkdir(parents=True, exist_ok=True)
    HOME_INFO.write_text(''.join(parts), encoding="utf-8")
