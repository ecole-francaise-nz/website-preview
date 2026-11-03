"""Integration tests in an isolated copy: graph exclusions and bilingual fallback."""
from pathlib import Path
import json
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
with tempfile.TemporaryDirectory(prefix='efia-search-test-') as directory:
    site = Path(directory)
    for folder in ['assets', 'config', 'content', 'data', 'layouts', 'static']:
        shutil.copytree(ROOT / folder, site / folder)
    def page(language, name, body):
        (site / 'content' / language / (name + '.md')).write_text('+++\ntitle = "' + name + '"\n+++\n' + body)
    page('en', 'search-test-english', 'English-only searchable fixture.')
    page('fr', 'search-test-french', 'Contenu uniquement en français.')
    page('en', 'search-test-private-a', '[B](/search-test-private-b/) [Unlinked PDF](/efia-flyer.pdf)')
    page('en', 'search-test-private-b', '[A](/search-test-private-a/)')
    with (site / 'content/en/about/team.md').open('a') as file:
        file.write('\n[English fixture](/search-test-english/?test=1#main-content)\n[French fixture](/fr/search-test-french/)\n[External](https://example.org/search-test-private-a/)\n')
    def build():
        subprocess.run(['hugo','--source',str(site),'--destination',str(site/'public')],check=True,capture_output=True)
        return [json.loads((site/'public'/name).read_text())['pages'] for name in ['index.json','fr/index.json']]
    en, fr = build()
    for index in [en,fr]:
        urls={p['url'] for p in index}
        assert '/search-test-english/' in urls and '/fr/search-test-french/' in urls
        assert '/search-test-private-a/' not in urls and '/search-test-private-b/' not in urls
        assert '/en/documents/about/efia-flyer.pdf' not in urls
    assert any(p['url']=='/fr/search-test-french/' and p['language']=='fr' for p in en)
    assert any(p['url']=='/search-test-english/' and p['language']=='en' for p in fr)
    # Linking a legacy URL from a reachable page should index only its canonical PDF.
    with (site / 'content/en/about/team.md').open('a') as file:
        file.write('\n[Linked PDF](/efia-flyer.pdf?t=1#page=1)\n')
    en, fr = build()
    for index in [en,fr]:
        urls={p['url'] for p in index}
        assert '/en/documents/about/efia-flyer.pdf' in urls
        assert '/efia-flyer.pdf' not in urls
    print('Passed orphan-page cycles, orphan PDFs, both language fallbacks, and canonical PDF reachability.')
