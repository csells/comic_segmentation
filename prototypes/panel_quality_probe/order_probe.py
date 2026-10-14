"""Diagnostic generic reading-order predicate against frozen automatic candidates."""
import argparse,sys
from pathlib import Path
from auto_convert import Client,Converter,read
from gemini_budget import Budget
from gemini_probe import save

ORDER_QUESTION={'type':'predicate','name':'order_defect','instructions':'''The supplied sequence reverses the narrative reading order of distinct target scenes. Independently trace the original page before comparing its numbered targets. Use visible actions and dialogue continuity: an inset may show an action preceding a larger overlapping consequence/reaction even if the larger scene begins farther left. Check each transition for reversed cause/effect or response before question. Do not rely solely on top-left positions, rectangular overlap, or the order in which crops were supplied. Respect explicit flashbacks and parallel action; do not invent chronology unsupported by the page. Incidental fragments from other scenes inside a crop do not change its target identity. Is the candidate target sequence genuinely wrong?'''}

def main():
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('output',type=Path);p.add_argument('--ledger',type=Path,required=True);p.add_argument('--pages',required=True);a=p.parse_args()
    key=sys.stdin.readline().strip();a.output.mkdir(parents=True,exist_ok=True)
    with Budget(a.ledger,cap=20000000) as budget:
        client=Client(key,budget,a.output/'calls');converter=Converter(client,a.output);results=[]
        for number in map(int,a.pages.split(',')):
            page=read(a.run/f'page-{number:04d}.json');candidate=page['selected'];bundle=read(Path(candidate['bundle']))
            answer,request=converter.decision(bundle,(Path(__file__).parent/'decisions-prompt-v2.txt').read_text(),[ORDER_QUESTION])
            result={'page':number,'answer':answer,'request':request};results.append(result);save(a.output/f'page-{number:04d}.json',result);print(result,flush=True)
        print('used/held',budget.used(),flush=True)
if __name__=='__main__':main()
