#!/usr/bin/env python3
"""
Génère sitemap.xml, llms.txt et llms-full.txt à partir des pages réelles du site.

Usage (depuis la racine du dépôt) :  python3 outils/generer-seo.py

- Toute nouvelle page ou nouvel article est inclus sans autre édition.
- Les pages en noindex et le dossier acces-prive/ sont exclus.
- La date de modification (lastmod) vient, dans l'ordre : de "dateModified" dans les données
  structurées de la page, de la mention « Dernière mise à jour : … » de la page, de la date du fichier.
- Le bloc de faits clés est écrit à la main dans outils/faits-cles.md : le relire
  avant chaque publication et le comparer aux pages légales.
"""
import html, os, re, sys, datetime
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://samaadi.be"
EXCLURE_DOSSIERS = {"acces-prive", "outils", "fonts", "images", "css", "js", ".git", ".github", "node_modules"}
EXCLURE_FICHIERS = {"404.html"}
MOIS = {m: i + 1 for i, m in enumerate(
    ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"])}


def trouver_pages():
    pages = []
    for dossier, sous, fichiers in os.walk(ROOT):
        sous[:] = [d for d in sous if d not in EXCLURE_DOSSIERS]
        for f in fichiers:
            if f.endswith(".html") and f not in EXCLURE_FICHIERS:
                pages.append(os.path.join(dossier, f))
    return sorted(pages)


def url_depuis_chemin(chemin):
    rel = os.path.relpath(chemin, ROOT).replace(os.sep, "/")
    if rel == "index.html":
        return BASE + "/"
    if rel.endswith("/index.html"):
        return BASE + "/" + rel[: -len("index.html")]
    return BASE + "/" + rel


class Texte(HTMLParser):
    """Texte visible en français : sans menu, pied de page, scripts, ni versions anglaises."""
    BLOCS = {"p", "h1", "h2", "h3", "h4", "li", "figcaption", "blockquote", "section", "header", "main", "div", "article", "figure"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.pile, self.buf, self.lignes = [], [], []

    def _masque(self, tag, a):
        return (tag in ("script", "style", "nav", "footer", "noscript", "video", "head", "title")
                or a.get("lang") == "en" or a.get("aria-hidden") == "true")

    def flush(self, niveau=None):
        t = re.sub(r"\s+", " ", "".join(self.buf)).strip()
        self.buf = []
        if t and not t.startswith("←"):
            self.lignes.append(("#" * (niveau + 1) + " " + t) if niveau else t)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("br", "img", "source", "meta", "link", "input"):
            if tag == "br" and not any(m for _, m in self.pile):
                self.buf.append(" ")
            return
        self.pile.append((tag, self._masque(tag, a)))
        if tag in self.BLOCS:
            self.flush()

    def handle_endtag(self, tag):
        niveau = int(tag[1]) if re.fullmatch(r"h[1-6]", tag) else None
        masque_avant = any(m for _, m in self.pile)
        while self.pile:
            t, _ = self.pile.pop()
            if t == tag:
                break
        if tag in self.BLOCS and not masque_avant:
            self.flush(niveau)

    def handle_data(self, data):
        if not any(m for _, m in self.pile):
            self.buf.append(data)


def lire_page(chemin):
    s = open(chemin, encoding="utf-8").read()
    g = lambda p: (re.search(p, s, re.S) or [None, None])[1]
    noindex = bool(re.search(r'<meta name="robots" content="[^"]*noindex', s, re.I))
    canon = g(r'<link rel="canonical" href="([^"]+)"') or url_depuis_chemin(chemin)
    titre = html.unescape(re.sub(r"\s+", " ", g(r"<title>(.*?)</title>") or "").strip())
    desc = g(r'<meta name="description" content="([^"]*)"') or ""
    desc = html.unescape(desc)
    lastmod = None
    m = re.search(r'"dateModified":\s*"(\d{4}-\d{2}-\d{2})', s)
    if m:
        lastmod = m.group(1)
    else:
        m = re.search(r"Dernière mise à jour\s*:\s*(\d{1,2})\s+([a-zéû]+)\s+(\d{4})", s)
        if m and m.group(2) in MOIS:
            lastmod = "%s-%02d-%02d" % (m.group(3), MOIS[m.group(2)], int(m.group(1)))
    if not lastmod:
        lastmod = datetime.date.fromtimestamp(os.path.getmtime(chemin)).isoformat()
        print("  ! pas de dateModified pour", os.path.relpath(chemin, ROOT), "-> date du fichier", file=sys.stderr)
    est_article = '"@type": "Article"' in s or '"@type":"Article"' in s
    publie = (re.search(r'"datePublished":\s*"(\d{4}-\d{2}-\d{2})', s) or [None, ""])[1]
    if canon != url_depuis_chemin(chemin):
        print("  ! canonical différent de l'adresse du fichier :", canon, "vs", url_depuis_chemin(chemin), file=sys.stderr)
    p = Texte(); p.feed(s); p.flush()
    corps, vus = [], set()
    for l in p.lignes:
        if l not in vus:
            vus.add(l); corps.append(l)
    return dict(chemin=chemin, url=canon, titre=titre, desc=desc, lastmod=lastmod, noindex=noindex,
                article=est_article, publie=publie, corps=corps)


def lire_faits():
    texte = open(os.path.join(ROOT, "outils", "faits-cles.md"), encoding="utf-8").read().splitlines()
    resume = " ".join(l[1:].strip() for l in texte if l.startswith(">"))
    faits = [l for l in texte if l.startswith("- ")]
    return resume, faits


def main():
    pages = [lire_page(c) for c in trouver_pages()]
    pages = [p for p in pages if not p["noindex"]]
    accueil = [p for p in pages if p["url"] == BASE + "/"]
    index_blog = [p for p in pages if p["url"] == BASE + "/blog/"]
    articles = sorted([p for p in pages if p["article"]], key=lambda p: p["publie"], reverse=True)
    deja = {id(p) for p in accueil + index_blog + articles}
    legales = sorted([p for p in pages if id(p) not in deja], key=lambda p: p["url"])
    ordre = accueil + index_blog + articles + legales

    # sitemap.xml
    out = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for p in ordre:
        out += ["  <url>", "    <loc>%s</loc>" % p["url"], "    <lastmod>%s</lastmod>" % p["lastmod"], "  </url>"]
    out.append("</urlset>")
    open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8").write("\n".join(out) + "\n")

    resume, faits = lire_faits()
    ligne = lambda p: "- [%s](%s)%s" % (p["titre"], p["url"], (": " + p["desc"]) if p["desc"] else "")

    # llms.txt
    t = ["# Samaâdi", "", "> " + resume, "", "## Faits clés", ""] + faits + ["", "## Pages", ""]
    t += [ligne(p) for p in accueil + index_blog]
    if articles:
        t += ["", "## Journal", ""] + [ligne(p) for p in articles]
    if legales:
        t += ["", "## Informations légales", ""] + [ligne(p) for p in legales]
    open(os.path.join(ROOT, "llms.txt"), "w", encoding="utf-8").write("\n".join(t) + "\n")

    # llms-full.txt
    f = ["# Samaâdi", "", "> " + resume, "", "## Faits clés", ""] + faits + [""]
    for p in ordre:
        f += ["---", "", "## " + p["titre"], "", "Adresse : " + p["url"], "Dernière modification : " + p["lastmod"], ""]
        f += [l + "\n" if l.startswith("#") else l for l in p["corps"]]
        f.append("")
    open(os.path.join(ROOT, "llms-full.txt"), "w", encoding="utf-8").write("\n".join(f) + "\n")
    print("OK :", len(ordre), "pages ->", "sitemap.xml, llms.txt, llms-full.txt")


if __name__ == "__main__":
    main()
