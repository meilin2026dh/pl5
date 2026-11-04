"""SQLite evidence ledger with provenance and conservative publication gates."""
from __future__ import annotations
import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from .collectors import Paper


def utcnow(): return datetime.now(timezone.utc).isoformat(timespec='seconds')

class LabStore:
    def __init__(self,path='runtime/autoresearch.sqlite'):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA busy_timeout=5000')
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS papers (
            key TEXT PRIMARY KEY, source TEXT NOT NULL, title TEXT NOT NULL,
            abstract TEXT NOT NULL, url TEXT NOT NULL, published TEXT,
            topic TEXT, authors TEXT, score REAL NOT NULL DEFAULT 0,
            first_seen TEXT NOT NULL, last_seen TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS hypotheses (
            fingerprint TEXT PRIMARY KEY, specification TEXT NOT NULL,
            first_paper_key TEXT NOT NULL, created_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'candidate',
            FOREIGN KEY(first_paper_key) REFERENCES papers(key));
        CREATE TABLE IF NOT EXISTS hypothesis_sources (
            fingerprint TEXT NOT NULL, paper_key TEXT NOT NULL,
            PRIMARY KEY(fingerprint,paper_key));
        CREATE TABLE IF NOT EXISTS trials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hypothesis TEXT NOT NULL, time TEXT NOT NULL,
            data_hash TEXT NOT NULL, phase TEXT NOT NULL,
            report TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS cycles (
            id INTEGER PRIMARY KEY AUTOINCREMENT, started TEXT, finished TEXT,
            fetched INTEGER, inserted INTEGER, errors TEXT);
        ''')
        self.db.execute("""CREATE TABLE IF NOT EXISTS literature_cards (
             id INTEGER PRIMARY KEY AUTOINCREMENT, paper_key TEXT NOT NULL,
             created_at TEXT NOT NULL, analyst_model TEXT NOT NULL,
             card_json TEXT NOT NULL, proposed_hypothesis TEXT)""")
        self.db.commit()
        from .prospective import initialize
        initialize(self.db)

    def close(self): self.db.close()
    def __enter__(self): return self
    def __exit__(self,*args): self.close()

    def upsert_papers(self,papers: list[Paper], score_fn) -> int:
        inserted=0
        for paper in papers:
            if not self.db.execute('SELECT 1 FROM papers WHERE key=?',(paper.key,)).fetchone(): inserted+=1
            self.db.execute('''INSERT INTO papers
                (key,source,title,abstract,url,published,topic,authors,score,first_seen,last_seen)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(key) DO UPDATE SET last_seen=excluded.last_seen,
                score=max(papers.score,excluded.score)''',
                (paper.key,paper.source,paper.title,paper.abstract,paper.url,paper.date,
                 paper.topic,paper.authors,score_fn(paper),utcnow(),utcnow()))
        self.db.commit()
        return inserted

    def papers(self,limit=100, min_score=0):
        return [dict(row) for row in self.db.execute(
            'SELECT * FROM papers WHERE score>=? ORDER BY score DESC,first_seen DESC LIMIT ?',
            (float(min_score),int(limit))).fetchall()]

    def add_hypothesis(self,spec, paper_key: str) -> bool:
        fp=spec.fingerprint()
        is_new=not self.db.execute('SELECT 1 FROM hypotheses WHERE fingerprint=?',(fp,)).fetchone()
        self.db.execute('INSERT OR IGNORE INTO hypotheses(fingerprint,specification,first_paper_key,created_at) VALUES (?,?,?,?)',
                        (fp,json.dumps(spec.as_dict(),ensure_ascii=False),paper_key,utcnow()))
        self.db.execute('INSERT OR IGNORE INTO hypothesis_sources(fingerprint,paper_key) VALUES (?,?)',(fp,paper_key))
        self.db.commit()
        return is_new

    def hypotheses(self,limit=300, status=None):
        q='SELECT h.*, (SELECT count(*) FROM hypothesis_sources s WHERE s.fingerprint=h.fingerprint) as sources FROM hypotheses h'
        args=[]
        if status:
            q+=' WHERE status=?'; args.append(status)
        q+=' ORDER BY created_at DESC LIMIT ?';args.append(int(limit))
        out=[]
        for row in self.db.execute(q,args):
            x=dict(row);x['specification']=json.loads(x['specification']);out.append(x)
        return out

    def set_status(self,fingerprint,status):
        if status not in ('candidate','lab_verified','shadow','rejected','approved'):
            raise ValueError('不允许的状态')
        if not self.db.execute('SELECT 1 FROM hypotheses WHERE fingerprint=?',(fingerprint,)).fetchone():
            raise KeyError('不存在的假设')
        # Scientific validity must not be claimed from a research-only trial.
        if status in ('lab_verified','approved'):
            raise ValueError('研究版不能自动授予预测有效/正式上线资格；须独立前瞻验证与单独发布流程')
        self.db.execute('UPDATE hypotheses SET status=? WHERE fingerprint=?',(status,fingerprint))
        self.db.commit()

    def papers_needing_analysis(self,limit=3,min_score=3,model=None):
        # Prevent repeated API spending on the same paper and model.
        if model is None:
            q='''SELECT p.* FROM papers p
                    WHERE p.score>=? AND NOT EXISTS
                     (SELECT 1 FROM literature_cards c WHERE c.paper_key=p.key)
                    ORDER BY p.score DESC,p.first_seen DESC LIMIT ?'''
            args=(float(min_score),int(limit))
        else:
            q='''SELECT p.* FROM papers p
                    WHERE p.score>=? AND NOT EXISTS
                     (SELECT 1 FROM literature_cards c WHERE c.paper_key=p.key AND c.analyst_model=?)
                    ORDER BY p.score DESC,p.first_seen DESC LIMIT ?'''
            args=(float(min_score),model,int(limit))
        return [dict(x) for x in self.db.execute(q,args).fetchall()]

    def add_literature_card(self,paper_key,card,spec=None):
        fingerprint=spec.fingerprint() if spec is not None else None
        self.db.execute("""INSERT INTO literature_cards
             (paper_key,created_at,analyst_model,card_json,proposed_hypothesis)
             VALUES(?,?,?,?,?)""",
             (paper_key,utcnow(),card['model'],json.dumps(card,ensure_ascii=False),fingerprint))
        if spec is not None:
            self.add_hypothesis(spec,paper_key)
        self.db.commit()

    def literature_cards(self,limit=50):
        rows=self.db.execute('SELECT * FROM literature_cards ORDER BY id DESC LIMIT ?',(int(limit),)).fetchall()
        out=[]
        for row in rows:
            d=dict(row)
            d['card']=json.loads(d.pop('card_json'))
            out.append(d)
        return out

    def record_trial(self,fingerprint,phase,data_hash,report):
        self.db.execute('INSERT INTO trials(hypothesis,time,data_hash,phase,report) VALUES(?,?,?,?,?)',
                        (fingerprint,utcnow(),data_hash,phase,json.dumps(report,ensure_ascii=False)))
        self.db.commit()

    def trials(self,limit=100):
        result=[]
        for row in self.db.execute('SELECT * FROM trials ORDER BY id DESC LIMIT ?',(int(limit),)):
            x=dict(row);x['report']=json.loads(x['report']);result.append(x)
        return result

    def record_cycle(self,fetched,inserted,errors):
        now=utcnow()
        self.db.execute('INSERT INTO cycles(started,finished,fetched,inserted,errors) VALUES(?,?,?,?,?)',
                        (now,now,int(fetched),int(inserted),json.dumps(errors,ensure_ascii=False)))
        self.db.commit()
