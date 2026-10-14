"""Research controller: automatic routing with injected, durable provider adapters.

No human-review callback. Providers own source/geometry validation, cache identity,
budget reservations and durable request/response records. This prototype does not
publish books or constitute the production rewrite.
"""


class RunBlocked(RuntimeError):
    """Budget, account or unknown request state: stop resumably, never certify."""


class PageBudgetExhausted(Exception):
    """The page reached its optional spend limit: stop escalating and fall back to the whole page."""


def _route(verdict):
    if not isinstance(verdict,dict) or verdict.get('route') not in ('keep','escalate'):
        raise RunBlocked('invalid quality verdict; no acceptance')
    return verdict['route']


def run_page(page, detect, refine, judge, verify, tiers=('sol-low','sol-high','astra'), repair=None, max_repairs=2, pixel_repair=None, *, final_accept, completeness_redetect=None, completeness_merge=None):
    if not callable(final_accept):
        raise TypeError('final_accept must be a callable; no implicit acceptance')
    if not tiers or len(tiers)>3 or len(set(tiers))!=len(tiers):
        raise ValueError('expected one to three distinct detector tiers')
    if type(max_repairs) is not int or not 0<=max_repairs<=2:
        raise ValueError('expected zero to two bounded repairs')
    attempts=[]
    def passes(candidate, attempt):
        verdict=judge(page,candidate);attempt['judge']=verdict
        if _route(verdict)!='keep':
            # Existing verifiers may clear only their own cheap quality alarms.
            confirmation=verify(page,candidate);attempt['verifier']=confirmation
            if _route(confirmation)!='keep':return False
        # The provider adapter validates and binds its proof to this candidate.
        # A rejection here advances bounded escalation, never verifier clearance.
        completeness=final_accept(page,candidate);attempt['completeness']=completeness
        return _route(completeness)=='keep'
    try:
        for tier in tiers:
            attempt={'tier':tier}; attempts.append(attempt)
            raw=detect(page,tier); attempt['raw']=raw
            candidate=refine(page,raw); attempt['candidate']=candidate
            if passes(candidate,attempt):
                return {'status':'accepted','selected':candidate,'attempts':attempts}
        for repair_round in range(1,max_repairs+1) if repair is not None else ():
            raw=repair(page,attempts[-1])
            if raw is None:break
            attempt={'tier':raw['tier'],'stage':'geometry-repair','repair_round':repair_round,'raw':raw};attempts.append(attempt)
            candidate=refine(page,raw);attempt['candidate']=candidate
            if passes(candidate,attempt):
                return {'status':'accepted','selected':candidate,'attempts':attempts}
            if raw.get('repair_changed') is False:break
        if pixel_repair is not None:
            raw=pixel_repair(page,attempts[-1])
            if raw is not None:
                attempt={'tier':raw['tier'],'stage':'component-repair','raw':raw};attempts.append(attempt)
                candidate=refine(page,raw);attempt['candidate']=candidate
                if passes(candidate,attempt):
                    return {'status':'accepted','selected':candidate,'attempts':attempts}
        rejection=attempts[-1].get('completeness',{})
        if (completeness_redetect is not None and isinstance(rejection,dict)
                and rejection.get('route')=='escalate' and rejection.get('disposition')=='missing'
                and rejection.get('unresolved')==[]):
            # The adapter must replay and bind the exact final missing proof.
            # This is one fresh detection, never a same-inventory repair parent.
            raw=completeness_redetect(page,attempts[-1])
            if raw is not None:
                attempt={'tier':raw['tier'],'stage':'completeness-redetection','raw':raw};attempts.append(attempt)
                candidate=refine(page,raw);attempt['candidate']=candidate
                if passes(candidate,attempt):
                    return {'status':'accepted','selected':candidate,'attempts':attempts}
                # A separate allowance of ONE clipping repair. Do not reset the
                # original max_repairs, repeat component repair, or redetect again.
                raw=repair(page,attempt) if repair is not None else None
                if raw is not None:
                    attempt={'tier':raw['tier'],'stage':'post-completeness-geometry-repair','repair_round':1,
                        'completeness_redetection_candidate':candidate.get('identity'),'raw':raw};attempts.append(attempt)
                    candidate=refine(page,raw);attempt['candidate']=candidate
                    if passes(candidate,attempt):
                        return {'status':'accepted','selected':candidate,'attempts':attempts}
        if completeness_merge is not None:
            # One deterministic merge of steps the final mapping never referenced, from the
            # latest bijection rejection. The merged candidate passes every normal check again.
            for previous in reversed(attempts):
                rejection=previous.get('completeness')
                if isinstance(rejection,dict) and rejection.get('route')=='escalate' and 'incomplete_bijection' in rejection.get('unresolved',[]):
                    raw=completeness_merge(page,previous)
                    if raw is not None:
                        attempt={'tier':raw['tier'],'stage':'completeness-merge','raw':raw};attempts.append(attempt)
                        candidate=refine(page,raw);attempt['candidate']=candidate
                        if passes(candidate,attempt):
                            return {'status':'accepted','selected':candidate,'attempts':attempts}
                    break
        return {'status':'whole_page_fallback','selected':None,'attempts':attempts,
                'reason':'bounded detector and repair attempts exhausted without a passing quality verdict'}
    except PageBudgetExhausted as error:
        return {'status':'whole_page_fallback','selected':None,'attempts':attempts,'reason':str(error)}
    except RunBlocked as error:
        return {'status':'blocked','selected':None,'attempts':attempts,'reason':str(error)}
