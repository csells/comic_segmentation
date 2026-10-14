"""Research-only durable spending reservations. Currency is integer micro-USD.

Standard Gemini 3.8 Flash price verified 2026-10-08: $0.75/M input,
$3.75/M output INCLUDING thinking, valid through 2026-12-31. No tools/caching.
Reserve $0.30, greater than 20k input + the full 65,536 model output limit.
Actual request output cap is smaller. Unknown usage keeps the full reservation.
This is a conservative token-price allowance, not a provider billing receipt.
"""
import fcntl
import json
import math
import os
from decimal import Decimal

RESERVE = 300000
CAP = 10000000


def usage_cost(usage, input_rate=0.75, output_rate=3.75):
    if 'promptTokenCount' not in usage or 'totalTokenCount' not in usage:
        return None
    inp, total = usage['promptTokenCount'], usage['totalTokenCount']
    if type(inp) is not int or type(total) is not int or not 0 <= inp <= total:
        raise ValueError('invalid usage; keep reservation')
    return math.ceil(Decimal(str(input_rate))*inp + Decimal(str(output_rate))*(total-inp))


class Budget:
    def __init__(self, path, cap=CAP):
        self.path, self.cap = path, cap
        self.entries = {}

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = self.path.open('a+')
        try:
            fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.file.seek(0)
            rows = [json.loads(line) for line in self.file]
            if not rows:
                self.append({'kind':'policy','cap':self.cap,'reserve':RESERVE,
                             'input_per_million_usd':0.75,'output_per_million_usd':3.75})
            elif rows[0].get('reserve') != RESERVE:
                raise ValueError('existing budget policy differs')
            effective_cap = rows[0]['cap'] if rows else self.cap
            for row in rows[1:]:
                if row['kind'] == 'reserve':
                    if row['id'] in self.entries:
                        raise ValueError('corrupt duplicate reservation')
                    self.entries[row['id']] = row
                elif row['kind'] == 'settle':
                    self.entries[row['id']]['cost'] = row['cost']
                elif row['kind'] == 'approved_cap_change':
                    effective_cap = row['cap']
            if effective_cap != self.cap:
                raise ValueError('existing budget cap differs; explicit approval amendment required')
            return self
        except BaseException:
            self.file.close()
            raise

    def append(self, event):
        self.file.write(json.dumps(event)+'\n')
        self.file.flush()
        os.fsync(self.file.fileno())

    def used(self):
        return sum(row['cost'] for row in self.entries.values())

    def approve_cap(self, new_cap, reason):
        if type(new_cap) is not int or new_cap < self.used() or not reason:
            raise ValueError('invalid cap amendment')
        self.append({'kind':'approved_cap_change','cap':new_cap,'reason':reason})
        self.cap = new_cap

    def reserve(self, identity, path, reservation=RESERVE, input_rate=0.75, output_rate=3.75):
        if identity in self.entries:
            raise ValueError('request already reserved; inspect/reuse its saved result')
        if reservation <= 0 or input_rate <= 0 or output_rate <= 0:
            raise ValueError('invalid reservation or rates')
        if self.used() + reservation > self.cap:
            raise ValueError('spending cap reached; no request sent')
        event = {'kind':'reserve','id':identity,'path':str(path),'cost':reservation,
                 'reservation':reservation,'input_rate':input_rate,'output_rate':output_rate}
        self.append(event)
        self.entries[identity] = event

    def settle(self, identity, usage):
        row = self.entries[identity]
        cost = usage_cost(usage,row.get('input_rate',0.75),row.get('output_rate',3.75))
        if cost is None:
            return
        if cost > row.get('reservation',RESERVE):
            raise ValueError('usage exceeded reservation; stop and investigate')
        self.append({'kind':'settle','id':identity,'cost':cost,'usage':usage})
        self.entries[identity]['cost'] = cost

    def __exit__(self, *_):
        self.file.close()
