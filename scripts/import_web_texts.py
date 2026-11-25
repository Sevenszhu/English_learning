#!/usr/bin/env python3
"""Import the reviewed online editions from a directory of downloaded HTML.

Raw filenames, URLs, retrieval checksums and selection boundaries are recorded
in reading_texts/source_audit.json. This importer deliberately selects complete
works or the complete chapters named in the reading list.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import html as html_std
import json
import re
import shutil
import unicodedata
from pathlib import Path
from xml.sax.saxutils import escape

from lxml import html

ROOT=Path(__file__).resolve().parents[1]
NAMES=['01_orwell','02_keynes','03_paine','04_swift','05_wilde',
       '06_smith','07_mill','08_douglass','09_dubois','10_burke']
IDS={3:31271,4:1080,5:1017,6:3300,7:34901,9:408,10:5655}
URLS={
 1:'https://www.orwellfoundation.com/the-orwell-foundation/orwell/essays-and-other-works/politics-and-the-english-language/',
 2:'https://www.economicsnetwork.ac.uk/archive/keynes_persuasion/Economic_Possibilities_for_our_Grandchildren.htm',
 8:'https://frederickdouglasspapersproject.com/s/digitaledition/item/16068',
}
for n,num in IDS.items():URLS[n]=f'https://www.gutenberg.org/ebooks/{num}'

# Complete words split by hard br tags in the Douglass Papers transcription.
WRAP_WORDS=set('''addressing properties however associations government judgement
unreasonable submitted measures agreement england colonial powerful interesting
circumstances attractiveness generation mammon multitudinous accepted themselves
nations distance favorable punishment forbidding christians affirmatively withering
conscience execration american driving arrival captivating antislavery starspangled
lawmakers ecclesiastics dependent esteem worship benevolence welcome religion
commission supported burchells millions bodyguards jefferson inconsistencies
interpreted established unconstitutionality unfashionable'''.split())


def norm(t):
    t=''.join(unicodedata.normalize('NFKC',c) if '\ufb00'<=c<='\ufb06' else c for c in t)
    for c in ['\u00a0','\u202f','\u2009']:t=t.replace(c,' ')
    t=t.replace('\u00ad','').replace('\u200b','').replace('\ufeff','')
    t=t.replace('—',' - ').replace('–','-').replace('‑','-').replace('‐','-').replace('−','-')
    return re.sub(r'\s+',' ',t).strip()


def rich(node, *, verse=False):
    """Keep only inline emphasis; all other source HTML is reduced to its text."""
    def walk(e):
        out=escape(e.text or '')
        for child in e:
            if not isinstance(child.tag,str):
                out+=escape(child.tail or '');continue
            tag=child.tag.lower()
            tail=child.tail or ''
            if tag=='br':
                value='\x00' if verse else ' '
                left=re.search(r"([A-Za-z’'-]+)$",re.sub(r'<[^>]*>','',out).rstrip())
                right=re.match(r"\s*([A-Za-z’'-]+)",tail)
                if not verse and left and right:
                    joined=re.sub('[^a-z]','',(left[1]+right[1]).lower())
                    if joined in WRAP_WORDS:value='';tail=tail.lstrip();out=out.rstrip()
            else:
                value=walk(child)
                if tag in ['em','i']:value='<i>'+value+'</i>'
                elif tag in ['strong','b']:value='<b>'+value+'</b>'
            out+=value+escape(tail)
        return out
    markup=walk(node)
    markup='<br/>'.join(norm(x) for x in markup.split('\x00')).strip()
    plain=html_std.unescape(re.sub(r'<[^>]*>','',markup.replace('<br/>','\n')))
    return {'text':plain,'markup':markup}


def element(node, kind='paragraph', *, verse=False):
    return {'kind':kind,**rich(node,verse=verse)}


def heading(t):return {'kind':'heading','text':t}


def siblings_until(h,tag='h2'):
    out=[]
    for e in h.itersiblings():
        if e.tag==tag:break
        out.append(e)
    return out


def source_doc(path):
    raw=path.read_bytes()
    match=re.search(br'<\?xml[^>]*encoding=["\']([^"\']+)',raw[:200])
    encoding=match[1].decode('ascii') if match else 'utf-8'
    doc=html.fromstring(raw,parser=html.HTMLParser(encoding=encoding))
    for e in doc.xpath('//script|//style|//span[contains(@class,"pagenum")]|//span[contains(@class,"pagenumber")]'):
        e.drop_tree()
    return doc,raw,encoding


def extract(n,doc,source_dir,old):
    out=[]
    if n==1:
        sec=doc.xpath('//article//section')[0]
        for e in sec:
            if e.tag=='p':
                if e.text_content().startswith('This material remains'):continue
                out.append(element(e))
            elif e.tag=='blockquote':
                out.extend(element(p,'quote') for p in e.xpath('./p'))
        # The Foundation stores its three author notes as mixed HTML outside p tags.
        notes=''.join(html.tostring(e,encoding='unicode',with_tail=True) for e in list(sec)[26:33])
        notes=(sec[25].tail or '')+notes
        note_doc=html.fromstring('<div>'+notes+'</div>')
        text=norm(note_doc.text_content())
        author_notes=re.split(r'(?=\[\d\])',text)
        note_elements=[{'kind':'note','text':t.strip()} for t in author_notes if t.strip()]
        assert len(note_elements)==3
        out[-1:-1]=note_elements
    elif n==2:
        prose=doc.xpath('//div[@class="prose"]')[0]
        for e in prose:
            t=norm(e.text_content())
            if t in ['I','II']:out.append(heading(t))
            elif e.tag=='p' or (e.tag=='div' and e.get('class')=='poem'):
                if e.tag=='div':e=e.xpath('./p')[0]
                item=element(e)
                if t.startswith("Don't mourn for me"):
                    item={'kind':'verse','text':t.replace(' never, For ',' never,\nFor ')}
                elif t.startswith('With psalms and sweet music'):
                    item={'kind':'verse','text':t.replace(' ringing, But ',' ringing,\nBut ')}
                out.append(item)
            elif e.tag=='blockquote':out.extend(element(p,'quote') for p in e.xpath('./p'))
            elif e.tag=='div' and 'margin-left' in e.get('style',''):
                ps=e.xpath('./p')
                out.extend(element(p,'quote') for p in ps)
                # The last spoken reply is mixed HTML outside the p elements.
                last=ps[-1]
                trailing=(last.tail or '')+''.join(html.tostring(x,encoding='unicode',with_tail=True)
                                                  for x in last.itersiblings())
                if norm(html.fromstring('<div>'+trailing+'</div>').text_content()):
                    out.append(element(html.fromstring('<div>'+trailing+'</div>'),'quote'))
        assert out[-1]['text'].endswith('that would be splendid!')
    elif n==3:
        h=next(x for x in doc.xpath('//h2') if 'AGRARIAN JUSTICE' in x.text_content())
        es=siblings_until(h)
        es=es[next(i for i,e in enumerate(es) if norm(e.text_content())=="AUTHOR'S INSCRIPTION."):]
        table_ix=0
        for e in es:
            t=norm(e.text_content())
            if e.tag=='p' and t:
                if t.startswith('To preserve the benefits'):out.append(heading('Agrarian Justice'))
                if t in ["AUTHOR'S INSCRIPTION.","AUTHOR'S ENGLISH PREFACE."] or t.startswith('MEANS '):
                    titles={"AUTHOR'S INSCRIPTION.":"Author's Inscription", "AUTHOR'S ENGLISH PREFACE.":"Author's English Preface"}
                    out.append(heading(titles.get(t,t.title())));continue
                item=element(e)
                # The Conway edition marks editorial apparatus with (1); retain
                # Paine's own Horsley note, which is identified separately below.
                for key in ['text','markup']:
                    item[key]=item[key].replace('(1)','').replace('(*)','[*]')
                    for a,b in [('hypocracy','hypocrisy'),('chief enterions','chief criterions'),
                                ('a principal that admits','a principle that admits'),
                                ('5,666,6667L.','5,666,666L.'),('get cut of that state','get out of that state'),
                                ('fund in rance','fund in France')]:
                        item[key]=item[key].replace(a,b)
                out.append(item)
            elif e.tag=='div' and e.get('class')=='fig':
                table=copy.deepcopy([e for e in old['elements'] if e['kind']=='table'][table_ix])
                out.append(table);table_ix+=1
            elif e.tag=='pre' and 'Horsley' in t:
                out.append({'kind':'note','text':t.replace('* Expression','[*] Expression')})
        assert table_ix==2
    elif n in [4,5]:
        ps=doc.xpath('//p')
        start=next(i for i,p in enumerate(ps) if norm(p.text_content()).startswith(
            'It is a melancholy object' if n==4 else 'The chief advantage'))
        end=next(i for i,p in enumerate(ps) if (
            'my wife past child-bearing.' in norm(p.text_content()) if n==4 else
            'The new Individualism is the new Hellenism.' in norm(p.text_content())))
        out=[element(p) for p in ps[start:end+1]]
    elif n==6:
        hs=[x for x in doc.xpath('//h2') if re.match(r'CHAPTER (I|II|III)\.',norm(x.text_content()))][:3]
        assert len(hs)==3
        for h in hs:
            out.append(heading(norm(h.text_content()).title()))
            notes=[]
            for p in h.getparent().xpath('./p'):
                item=element(p)
                for key in ['text','markup']:
                    item[key]=re.sub(r'\{this was the current designation for\s+steam engines\}', '[1]',item[key],flags=re.I)
                if '[1]' in item['text']:notes.append({'kind':'note','text':'[1] This was the current designation for steam engines.'})
                out.append(item)
            if notes:out.extend([heading('Note'),*notes])
    elif n==7:
        h=next(x for x in doc.xpath('//h2') if 'CHAPTER II.' in x.text_content())
        for e in siblings_until(h):
            if e.tag=='p' and norm(e.text_content()):out.append(element(e))
            elif e.tag=='div' and e.get('class')=='footnotes':
                out.append(heading('Footnotes'))
                out.extend(element(p,'note') for p in e.xpath('.//p'))
    elif n==8:
        for sup in doc.xpath('//tei//sup'):
            if sup.text_content().strip()=='*':
                for child in list(sup):sup.remove(child)
                sup.tag='span';sup.text='[*]'
        for e in doc.xpath('//sup|//span[contains(@class,"tooltiptext")]|//span[contains(@class,"-teibp-pageNum")]'):
            e.drop_tree()
        ps=doc.xpath('//tei//p')
        start=next(i for i,p in enumerate(ps) if norm(p.text_content()).startswith('Mr. President, Friends'))
        previous_page=None
        for p in ps[start:]:
            t=norm(p.text_content())
            if not t:continue
            is_poem=any(t.startswith(x) for x in ['God speed the year','God speed the day',
                                                'God speed the hour','Until that year'])
            item=element(p,'verse' if is_poem else 'paragraph',verse=is_poem)
            parent=p.getparent()
            # The transcription's div elements are printed page boundaries.
            # Merge only the first p on a new page with the preceding p when
            # that printed page starts in the middle of a paragraph.
            first_in_page=not p.xpath('preceding-sibling::p')
            continuation=(out and first_in_page and parent is not previous_page
                          and not is_poem and out[-1]['kind']=='paragraph')
            # These printed pages start with a genuine new paragraph.
            if any(t.startswith(x) for x in ['But, such is not the state',
                                            'Let this damning fact',
                                            'Let the religious press',
                                            'Fellow-citizens! there is no matter']):continuation=False
            if continuation:
                out[-1]['text']+=' '+item['text']
                out[-1]['markup']+=' '+item['markup']
            else:out.append(item)
            previous_page=parent
        for item in out:
            for key in ['text','markup']:
                for a,b in [('whosejudgement','whose judgement'),('ofthe','of the'),
                            ('Africal!','Africa!'),('to how] in the','to howl in the'),
                            ('ln speaking of','In speaking of'),('darkest comers of','darkest corners of'),
                            ('nation ’s','nation’s'),('form of wor - ship','form of worship'),
                            ('enactments for bidding','enactments forbidding')]:
                    item[key]=item[key].replace(a,b)
        out.append({'kind':'note','text':"[*] Rev. R. R. Raymond. (Author's note.)"})
    elif n==9:
        h=next(x for x in doc.xpath('//h2') if 'Of the Dawn of Freedom' in norm(x.text_content()))
        for e in h.getparent():
            if e.tag=='p' and norm(e.text_content()):
                out.append(element(e,'verse' if e.get('class')=='poem' else 'paragraph',
                                   verse=e.get('class')=='poem'))
            elif e.tag=='div' and e.get('class')=='fig':
                asset=ROOT/'reading_texts/assets/09_score2.jpg'
                asset.parent.mkdir(exist_ok=True)
                shutil.copyfile(source_dir/'09_score2.jpg',asset)
                out.append({'kind':'image','file':'reading_texts/assets/09_score2.jpg',
                            'alt':'Musical epigraph from The Souls of Black Folk, Chapter II',
                            'sha256':hashlib.sha256(asset.read_bytes()).hexdigest()})
    elif n==10:
        for e in doc.xpath('//a[starts-with(@href,"#linknote-")]'):e.drop_tree()
        h=[x for x in doc.xpath('//h2') if norm(x.text_content())=='EDMUND BURKE'][-1]
        ps=[e for e in siblings_until(h) if e.tag=='p' and norm(e.text_content())]
        out=[element(p) for p in ps[1:]]
    return [e for e in out if e['kind'] in ['table','image'] or e.get('text','').strip()]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_dir',type=Path)
    args=parser.parse_args()
    summaries=[]
    for n,name in enumerate(NAMES,1):
        path=next((ROOT/'reading_texts').glob(f'{n:02d}_*.json'))
        old=json.loads(path.read_text())
        doc,raw,encoding=source_doc(args.source_dir/(name+'.html'))
        elements=extract(n,doc,args.source_dir,old)
        assert elements
        texts=[e['text'] for e in elements if 'text' in e]
        text='\n\n'.join(texts)
        assert '\ufffd' not in text, f'Encoding error in {name}'
        if n==10:
            assert texts[0].startswith('I hope, Sir,')
            assert texts[-1].endswith('the High Court of Parliament."')
            assert len(text.split())>23000
        if n==6:assert sum(e['kind']=='heading' and e['text'].startswith('Chapter ') for e in elements)==3
        if n==7:
            assert '[6]' in text and '[10]' in text
            assert 'never to return?' in texts[-1]
        if n==9:assert sum(e['kind']=='image' for e in elements)==1
        data={k:v for k,v in old.items() if k not in ['original_pdf','original_sha256','original_pages','elements','proofreading_sources']}
        if 'previous_pdf' not in data:
            data['previous_pdf']={'path':old['original_pdf'],'sha256':old['original_sha256'],'git_commit':'7b38e2f'}
        data['repository_pdf']=data['previous_pdf']['path']
        retrieval=URLS[n]
        if n in IDS:
            num=IDS[n]
            retrieval=f'https://mirror.fi.ossplanet.net/gutenberg/{"/".join(str(num)[:-1])}/{num}/{num}-h/{num}-h.htm'
        scope='Complete article'
        if n==3:scope='Complete tract, French inscription and English preface; Conway edition'
        if n==6:scope='Book I, complete Chapters I-III'
        if n==7:scope='Complete Chapter II, including author footnotes [6]-[10]'
        if n==8:scope='Complete speech and closing poem; modern editorial annotations excluded'
        if n==9:scope='Complete Chapter II, verse epigraph and musical epigraph'
        if n==10:scope='Complete speech, March 22, 1775; school editor introduction and notes excluded'
        data['web_source']={'url':URLS[n],'retrieval_url':retrieval,'retrieved_on':'2026-11-26',
                            'raw_sha256':hashlib.sha256(raw).hexdigest(),'encoding':encoding,'scope':scope}
        data['source_url']=URLS[n]
        if n in IDS:data['source_label']=f'Project Gutenberg, eBook {IDS[n]}'
        if n==3:
            data['subtitle']='With the French inscription and English preface'
            data['source_label']='The Writings of Thomas Paine, Volume III (Conway); Project Gutenberg 31271'
            data['transcription_repairs']=[['hypocracy','hypocrisy'],['chief enterions','chief criterions'],
                                           ['a principal that admits','a principle that admits'],
                                           ['5,666,6667L.','5,666,666L.'],['get cut of that state','get out of that state'],
                                           ['fund in rance','fund in France']]
        if n==8:data['source_label']='Frederick Douglass Papers Project, Digital Edition'
        if n==10:data['subtitle']='Complete speech delivered in the House of Commons, March 22, 1775'
        data['elements']=elements
        path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
        summary={'number':n,'title':data['title'],**data['web_source'],
                 'elements':len(elements),'words':len(text.split()),
                 'first_passage':texts[0][:160],'last_passage':texts[-1][-160:],
                 'text_sha256':hashlib.sha256(text.encode()).hexdigest()}
        summaries.append(summary)
        (args.source_dir/(name+'-selected.txt')).write_text(text)
        print(n,len(elements),len(text.split()),texts[0][:45],flush=True)
    (ROOT/'reading_texts/source_audit.json').write_text(json.dumps(summaries,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
