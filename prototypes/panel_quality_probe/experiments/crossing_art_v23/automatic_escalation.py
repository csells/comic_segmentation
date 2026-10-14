"""Research controller: automatic routing with injected, durable provider adapters.

No human-review callback. Providers own source/geometry validation, cache identity,
budget reservations and durable request/response records. This prototype does not
publish books or constitute the production rewrite.
"""


class RunBlocked(RuntimeError):
    """Budget, account or unknown request state: stop resumably, never certify."""


def _route(verdict):
    if not isinstance(verdict,dict) or verdict.get('route') not in ('keep','escalate'):
        raise RunBlocked('invalid quality verdict; no acceptance')
    return verdict['route']


def run_page(page, detect, refine, judge, verify, tiers=('sol-low','sol-high','astra')):
    if not tiers or len(tiers)>3 or len(set(tiers))!=len(tiers):
        raise ValueError('expected one to three distinct detector tiers')
    attempts=[]
    try:
        for tier in tiers:
            attempt={'tier':tier}; attempts.append(attempt)
            raw=detect(page,tier); attempt['raw']=raw
            candidate=refine(page,raw); attempt['candidate']=candidate
            verdict=judge(page,candidate); attempt['judge']=verdict
            if _route(verdict)=='keep':
                return {'status':'accepted','selected':candidate,'attempts':attempts}
            # A richer automatic verifier can dismiss a cheap judge's false alarm
            # before paying for a new detector pass. It must return a valid verdict.
            confirmation=verify(page,candidate); attempt['verifier']=confirmation
            if _route(confirmation)=='keep':
                return {'status':'accepted','selected':candidate,'attempts':attempts}
        return {'status':'whole_page_fallback','selected':None,'attempts':attempts,
                'reason':'detector tiers exhausted without a passing quality verdict'}
    except RunBlocked as error:
        return {'status':'blocked','selected':None,'attempts':attempts,'reason':str(error)}
