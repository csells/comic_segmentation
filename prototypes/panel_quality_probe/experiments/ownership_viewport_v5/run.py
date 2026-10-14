"""Bounded source-audit/viewport experiment; execute only inside VM153."""
import copy,hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]))
sys.path.insert(0,str(HERE.parent/'scene_identity_v1'))
from auto_convert import Client
from gemini_budget import Budget
from gemini_probe import save
from scene_evidence import request_body,response_evidence,evidence_gate,verifier_hypotheses
from target_detail import with_source_detail
from escalation_probe import parse_verdict
# Unchanged previous treatment wrapper; no tuning after its recorded failure.
from experiments.scene_identity_v1.protocol import verifier_body
from experiments.scene_identity_v1.run import structural_score

ROOT=Path('/home/tester/comic-reader')
OUT=ROOT/'evidence/ownership-viewport-v5-funded-recovery-20261009'
LEDGER=ROOT/'evidence/gemini-10usd-20261008.jsonl'
LIMIT=5_000_000
MAX_NEW=11
REJECTED_REQUEST='523696e1387921f9625ea11a32a215d84032944ad84a9904c6ce3859099b6405'
AUDITS=['original150','erased150','corrected150','final57']
# Evaluation-only expected answers. No model request contains these labels.
CHECKS=[('original150','original150',3,'defect'),('erased150','erased150',3,'defect'),
        ('corrected150','corrected150-padded',3,'intact'),
        ('corrected150','corrected150-padded',2,'intact'),
        ('final57','final57-padded',8,'intact'),('final57','final57-padded',10,'intact'),
        ('original150','original150-padded',3,'defect')]


def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def used(entries):return sum(r['cost'] for r in entries.values() if Path(r['path']).is_relative_to(OUT))


class SpikeBudget(Budget):
    def reserve(self,identity,path,reservation,input_rate,output_rate):
        scoped=[r for r in self.entries.values() if Path(r['path']).is_relative_to(OUT)]
        if len(scoped)>=MAX_NEW or used(self.entries)+reservation>LIMIT:
            raise ValueError('Ownership/viewport request or $5 limit reached')
        if not Path(path).is_relative_to(OUT):raise ValueError('Unscoped reservation')
        super().reserve(identity,path,reservation,input_rate,output_rate)


def bundle(name):
    return read(OUT/name/'bundle.json' if name.endswith('-padded') else OUT/(name+'-bundle.json'))


def prepare():
    if (OUT/'run.json').exists():raise ValueError('Already frozen')
    erased=copy.deepcopy(bundle('original150'))
    found=0
    for p in erased['panels']:
        if 'flower-decorated' in p['description']:
            p['description']=p['description'].replace('flower-decorated ','');found+=1
    if found!=1:raise ValueError('Natural omission control changed')
    save(OUT/'erased150-bundle.json',erased)
    for audit in AUDITS:request_body(bundle(audit),model='gpt-6-astra')
    for i,(_,name,target,_) in enumerate(CHECKS):
        detail=with_source_detail(bundle(name),target,OUT/'details'/str(i),mark_boundary=True)
        # Raw detector descriptions are audited separately, not repeated as facts.
        detail['panels']=[{'order':p['order'],'box':p['box']} for p in detail['panels']]
        save(OUT/f'check-{i}-bundle.json',detail)
    files=[*HERE.glob('*.py'),*[HERE.parents[1]/n for n in ['scene_evidence.py','scene-evidence-prompt-v1.txt',
        'viewport_refine.py','auto_convert.py','gemini_budget.py','gemini_probe.py','openai_probe.py',
        'target_detail.py','escalation_probe.py','judge-target-detail-prompt-v2.txt']],
        *[HERE.parent/'scene_identity_v1'/n for n in ['protocol.py','run.py','auxiliary-prompt.txt']],
        *OUT.glob('*bundle.json'),*[OUT/n/'bundle.json' for n in ['original150-padded','corrected150-padded','final57-padded']]]
    save(OUT/'run.json',{'source_audit_model':'gpt-6-astra','single_change':'One explicitly named quota-rejection recovery after confirmed credit restoration; same V4 source/crop request bodies', 'rejected_request':REJECTED_REQUEST,'frozen_at':datetime.now(timezone.utc).isoformat(),'purpose':'Source audit corrects naturally wrong/incomplete detector hints; bounded margins preserve thin edges',
        'audits':AUDITS,'checks':CHECKS,'local_cap_micro_usd':LIMIT,'max_new_calls':MAX_NEW,
        'fault_injection':'erased150 removes only flower-decorated from real saved detector text; no replacement gold identity',
        'stop':'Source audit unavailable skips its dependent checks; any harmful crop acceptance stops all remaining crop calls; invalid/unknown response stops run.',
        'evaluation_basis':'Fresh source/all13padded57+all3corrected150 review completed before inference; original150 remains incomplete after padding.',
        'frozen_files':{str(p):sha(p) for p in files}})
    print('Frozen four source audits and seven crop checks; zero calls',flush=True)


def execute():
    if (OUT/'terminal.json').exists():raise ValueError('Terminal experiment; no replay')
    m=read(OUT/'run.json')
    for path,digest in m['frozen_files'].items():
        if sha(Path(path))!=digest:raise ValueError('Frozen file changed: '+path)
    if datetime.now(timezone.utc).date().isoformat()>'2026-12-31':raise ValueError('Expired pricing')
    key=sys.stdin.readline().strip()
    if not key.startswith('sk-'):raise ValueError('Credential missing')
    audits={};results=[];reason=None
    with SpikeBudget(LEDGER,cap=100_000_000) as budget:
        client=Client(key,budget,OUT/'calls',retry_rejected={REJECTED_REQUEST})
        try:
            for index,name in enumerate(AUDITS,1):
                print(f'[source audit {index}/{len(AUDITS)}] {name}',flush=True)
                b=bundle(name)
                raw,req=client.request('responses',request_body(b,model='gpt-6-astra'),'verifier')
                evidence=response_evidence(raw,b,req,model='gpt-6-astra',request_kind='verifier')
                gate=evidence_gate(evidence,b)
                audits[name]={'evidence':evidence,'gate':gate}
                save(OUT/(name+'-evidence.json'),audits[name])
                print(json.dumps({'source_audit':name,'gate':gate,'result':evidence['result']}),flush=True)
            for index,(audit,name,target,expected) in enumerate(CHECKS):
                print(f'[crop check {index+1}/{len(CHECKS)}] {name} target {target}, audit {audit}',flush=True)
                ev=audits[audit]['evidence'];b=bundle(name)
                # Explicit link only for source-identical monotonic viewport descendants.
                frozen=ev['proposal_sha256'] if name.endswith('-padded') else None
                gate=evidence_gate(ev,b,frozen_proposal_sha256=frozen)
                if gate['route']!='keep':
                    result={'index':index,'audit':audit,'case':name,'target':target,'status':'skipped-unresolved-source','gate':gate,'routing_pass':False}
                else:
                    hypotheses=verifier_hypotheses(ev,b,frozen_proposal_sha256=frozen)
                    detail=read(OUT/f'check-{index}-bundle.json')
                    raw,req=client.request('responses',verifier_body(detail,hypotheses,'identity'),'verifier')
                    verdict=parse_verdict(raw,len(b['panels']))
                    result={'index':index,'audit':audit,'case':name,'target':target,'status':'checked','verdict':verdict,'request':req,
                            **structural_score(verdict,expected,target)}
                results.append(result);save(OUT/f'check-{index}-result.json',result)
                print(json.dumps(result),flush=True)
                if result.get('harmful_accept'):raise ValueError('Known defective crop accepted; variant stopped')
        except Exception as error:
            reason=str(error).replace(key,'[REDACTED]')
            raise
        finally:
            save(OUT/'terminal.json',{'reason':reason,'audit_count':len(audits),'results':results,
                'not_completed':CHECKS[len(results):],
                'routing_gate_pass':reason is None and len(results)==len(CHECKS) and all(r['routing_pass'] for r in results),
                'visual_evidence_review':'pending; routing is not independent evidence',
                'new_calls':client.new_calls,'cache_hits':client.cache_hits,'spike_used_or_held_micro_usd':used(budget.entries),
                'total_used_or_held_micro_usd':budget.used()})


if __name__=='__main__':
    if sys.argv[1:] == ['prepare']:prepare()
    elif sys.argv[1:] == ['execute-after-credit-restoration']:execute()
    else:raise ValueError('Expected prepare or execute-after-credit-restoration')
