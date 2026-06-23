#!/usr/bin/env python3
"""Build the public "Probability Toolbox" section from the private Obsidian vault.

Pipeline (matches the vault's own Public Publishing Plan, Option B):
  1. Select a curated, privacy-checked subset of notes (ALLOW minus BLOCK).
  2. Strip YAML frontmatter; resolve [[wikilinks]] among the published set only
     (links to unpublished notes degrade to plain text -- never a leak, never a 404).
  3. Convert Markdown -> HTML with pandoc, leaving math for MathJax.
  4. Wrap each page in the shared site stylesheet (../style.css); build a landing index.

Re-run any time after editing the vault:  python3 build/build_toolbox.py

SAFETY: BLOCK is a hard never-publish list enforced regardless of ALLOW or any
publish:true flag. Whole folders (Inbox, Personal Research Identity, ...) are
never even traversed.
"""
import os, re, subprocess, sys

VAULT = "/home/potato_eat_potato/math-lib"
SITE  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT   = os.path.join(SITE, "toolbox")

# --- folders never traversed for publishing --------------------------------
SKIP_DIRS = {"00 Inbox", "09 Public Website", "10 Personal Research Identity",
             "99 Archive", "Templates", ".git", ".obsidian", "build"}

# --- hard block: never emit, even if allowlisted or flagged publish:true ----
BLOCK = {
    "My Research Questions", "CV-to-Toolbox Map", "My Public Website Vision",
    "Public Publishing Plan", "My Mathematical Route",
    "My Probability Research Identity", "My Reading Timeline",
    "My Talks and Expositions", "Why I Am Building This Toolbox",
    "DGFF on punctured box", "Random walk on box with mesoscopic hole",
    "Harmonic measure near removed set",
    "Raw - does the punctured DGFF see the puncture in its maximum",
    "HOME", "README",
}

# --- curated allowlist: safe + appropriate for a public research toolbox ----
ALLOW = {
    # Tools (15)
    "Turn hitting probability into harmonic function",
    "Turn random walk into electrical network",
    "Use effective resistance to control random walk",
    "Use Thomson principle by constructing flow",
    "Use Rayleigh monotonicity by shorting or cutting",
    "Use Green function as inverse Laplacian",
    "Express DGFF covariance by Green function",
    "Use Gaussian conditioning as Markov property",
    "Use first moment method for maximum upper bound",
    "Use second moment method for existence lower bound",
    "Use Cramer transform for large deviation speed",
    "Regularize infinite graph by finite box",
    "Replace divergent Green function by potential kernel",
    "Use multiscale decomposition",
    "Compare domains by monotonicity",
    # Objects (13)
    "Simple random walk on Z2", "Green function", "Killed Green function",
    "Effective resistance", "Dirichlet energy", "Discrete Laplacian",
    "Potential kernel", "DGFF", "Branching random walk", "Legendre transform",
    "Harmonic measure", "Unit current flow", "Equilibrium potential",
    # Theorems (8)
    "Optional stopping theorem", "Strong Markov property", "Thomson principle",
    "Dirichlet principle", "Rayleigh monotonicity", "Maximum principle",
    "Gaussian conditioning formula", "Cramer theorem",
    # Proof patterns (8; Boundary-to-bulk held back -- has the punctured-box computation)
    "First moment upper bound", "Second moment lower bound",
    "Finite volume approximation", "Energy minimization argument",
    "Multiscale decomposition", "Entropy versus energy", "Change of measure",
    "Union bound over exponential family",
    # Maps (6; Research Problem Map / DGFF Map / My Probability Research Route held back)
    "Probability Toolbox Map", "Tool Index",
    "Random Walk and Electrical Networks Map",
    "Green Function and Potential Theory Map",
    "Branching Random Walk Map", "Large Deviations Map",
    # Talks & expositions (4)
    "HRUMC Talk - A Harmonic View of Random Walks and Electrical Networks",
    "Courant Seminar Talk - Lattice Random Walks and Electrical Networks",
    "Exposition - Why Green Functions Connect Random Walks and DGFF",
    "Exposition - Effective Resistance as a Probability Tool",
    # Problems (2 benchmark; research-candidate problems held back)
    "Effective resistance between adjacent vertices in Z2",
    "Escape probability of SRW on Z2",
}

# source folder -> (sort order, section title, one-line descriptor)
SECTION = {
    "01 Maps":                 (1, "Maps", "How the areas connect — start here."),
    "02 Tools":                (2, "Tools", "Reusable mathematical moves — the core of the toolbox."),
    "03 Objects":              (3, "Objects", "The recurring nouns and what links them."),
    "04 Theorems":             (4, "Theorems", "Results I lean on, with intuition and failure modes."),
    "05 Proof Patterns":       (5, "Proof patterns", "Reusable proof skeletons."),
    "06 Problems":             (6, "Problems", "Worked benchmark problems."),
    "08 Talks and Expositions":(7, "Talks & expositions", "Talks given and write-ups in progress."),
}
TYPE_LABEL = {"tool": "Tool", "object": "Object", "theorem": "Theorem",
              "proof-pattern": "Proof pattern", "problem": "Problem",
              "map": "Map", "talk": "Talk / exposition"}

INTRO = ("A working toolbox for probability research — notes organized not by "
         "textbook topic but by reusable <em>moves</em>: ways to recognize a structure, "
         "choose a tool, or attack a problem. It grows out of my reading and talks on "
         "random walks, electrical networks, Green functions, and the discrete Gaussian "
         "free field. It is deliberately a living document: some notes are polished, "
         "others are still developing. The organizing belief is simple — knowledge "
         "you can reuse is worth writing down as an action.")

WIKILINK = re.compile(r"\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]")


def slug(name):
    s = name.lower().replace("&", " and ")
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s).strip("-")
    return re.sub(r"-+", "-", s)


def split_front(text):
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    return (m.group(1), m.group(2)) if m else ("", text)


def fm_get(fm, key):
    m = re.search(r"^%s:\s*(.+)$" % re.escape(key), fm, re.M)
    return m.group(1).strip().strip('"') if m else ""


def resolve_links(md, pub):
    def repl(m):
        target, alias = m.group(1).strip(), (m.group(2) or m.group(1)).strip()
        sl = pub.get(target)
        return "[%s](%s.html)" % (alias, sl) if sl else alias
    return WIKILINK.sub(repl, md)


def to_html(md):
    p = subprocess.run(
        ["pandoc",
         "--from=markdown+tex_math_dollars+pipe_tables-yaml_metadata_block",
         "--to=html5", "--mathjax"],
        input=md, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(p.stderr)
    return p.stdout


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{TITLE}} · Probability Toolbox</title>
<link rel="stylesheet" href="../style.css">
<script>
window.MathJax = {
  tex: { inlineMath: [['\\\\(','\\\\)']], displayMath: [['\\\\[','\\\\]']] },
  options: { skipHtmlTags: ['script','noscript','style','textarea','pre','code'] }
};
</script>
<script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
</head>
<body>
<nav class="crumb"><a href="../index.html">Sicheng (Sam) Wang</a> &rsaquo; <a href="index.html">Probability Toolbox</a></nav>
<p class="kicker">{{KICKER}}</p>
<article>
{{BODY}}
</article>
<footer>A living research toolbox · <a href="index.html">all notes</a> · Sicheng (Sam) Wang</footer>
</body>
</html>
"""

INDEX = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Probability Toolbox · Sicheng (Sam) Wang</title>
<meta name="description" content="A working toolbox for probability research: random walks, electrical networks, Green functions, and the discrete Gaussian free field, organized around reusable mathematical tools.">
<link rel="stylesheet" href="../style.css">
</head>
<body>
<nav class="crumb"><a href="../index.html">Sicheng (Sam) Wang</a> &rsaquo; Probability Toolbox</nav>
<h1>Probability Toolbox</h1>
<p class="intro">{{INTRO}}</p>
{{SECTIONS}}
<footer>A living research toolbox · Sicheng (Sam) Wang</footer>
</body>
</html>
"""


def main():
    notes = []  # (basename, folder, path)
    for root, dirs, files in os.walk(VAULT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        folder = os.path.basename(root)
        for f in sorted(files):
            if not f.endswith(".md"):
                continue
            base = f[:-3]
            if base in BLOCK or base not in ALLOW:
                continue
            notes.append((base, folder, os.path.join(root, f)))

    pub = {base: slug(base) for base, _, _ in notes}

    leaked = [b for b in pub if b in BLOCK]
    if leaked:
        sys.exit("ABORT: blocked notes in publish set: %s" % leaked)

    os.makedirs(OUT, exist_ok=True)
    for old in os.listdir(OUT):                      # clear stale pages (renames, removals)
        if old.endswith(".html"):
            os.remove(os.path.join(OUT, old))

    by_section = {}
    for base, folder, path in notes:
        with open(path, encoding="utf-8") as fh:
            fm, body = split_front(fh.read())
        kicker = TYPE_LABEL.get(fm_get(fm, "type"), "Note")
        body_html = to_html(resolve_links(body, pub))
        page = (PAGE.replace("{{TITLE}}", base)
                    .replace("{{KICKER}}", kicker)
                    .replace("{{BODY}}", body_html))
        with open(os.path.join(OUT, slug(base) + ".html"), "w", encoding="utf-8") as fh:
            fh.write(page)
        order, title, desc = SECTION.get(folder, (99, "Other", ""))
        by_section.setdefault((order, title, desc), []).append(base)

    blocks = []
    for (order, title, desc) in sorted(by_section):
        items = "\n".join(
            '    <li><a href="%s.html">%s</a></li>' % (slug(b), b)
            for b in sorted(by_section[(order, title, desc)]))
        blocks.append(
            '<section class="group">\n  <h2>%s</h2>\n  <p class="desc">%s</p>\n  <ul>\n%s\n  </ul>\n</section>'
            % (title, desc, items))
    index = INDEX.replace("{{INTRO}}", INTRO).replace("{{SECTIONS}}", "\n".join(blocks))
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(index)

    print("Published %d notes -> %s" % (len(notes), OUT))
    for (order, title, desc) in sorted(by_section):
        print("  %-22s %d" % (title, len(by_section[(order, title, desc)])))


if __name__ == "__main__":
    main()
