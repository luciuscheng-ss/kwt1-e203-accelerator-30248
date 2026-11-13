import re
from pathlib import Path
def lines(p):return Path(p).read_text().splitlines()
def need(x,m):
 if not x:raise ValueError(m)
def annotation(path):
    text=lines(path);titles=('switching activity','static probability');sections=[]
    for i,row in enumerate(text):
        normalized=' '.join(row.lower().split())
        for title in titles:
            if normalized==title+' overview statistics for "e203_soc_top"':sections.append((title,i))
    need([x[0] for x in sections]==list(titles),'Both whole-SoC activity and probability tables are required')
    counts=[]
    for n,(title,start) in enumerate(sections):
        end=sections[n+1][1] if n+1<len(sections) else len(text);part=text[start:end]
        header=' '.join(' '.join(part[:6]).lower().split())
        need(re.search(r'from\s+activity',header) and re.search(r'file\s*\(\s*%\s*\)',header),'Unreviewed activity/probability column headers')
        rows=[x for x in part if re.match(r'^\s*Nets\s+\d',x)]
        need(len(rows)==1,'Expected one Nets row in each actual statistics table')
        values=re.findall(r'(\d+)\(\s*([\d.]+)%\)',rows[0])
        need(len(values)==10,'Unreviewed actual PT2022 statistics column count')
        need(int(values[0][0])>0 and float(values[0][1])==100 and all(int(a)==0 and float(b)==0 for a,b in values[1:]),'Missing/default/propagated activity or static probability requires new review')
        counts.append(int(values[0][0]))
    need(counts[0]==counts[1],'Activity and static-probability populations differ')
    return counts[0]

