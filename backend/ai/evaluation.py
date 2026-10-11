"""Transparent offline M6 semantic-admission scoring for developer-labeled examples.

Gold labels are supplied by an explicit synthetic test fixture. This scorer
does NOT infer whether generated text is entailed by real source documents.
It detects whether the production admission decision contradicts gold labels.
No external model or network use.
"""
from collections import Counter

LABELS=frozenset({"SUPPORTED","UNSUPPORTED","ABSTENTION"})


def evaluate_labeled_decisions(rows):
    """Score tuples of (case_id, developer_gold_label, contract_admitted).

    A successful *evaluation test* can report STOP: that means the current
    model-output validator admitted examples the developer labeled unsupported.
    Do not interpret a passing test run as semantic-model admission.
    """
    seen=set()
    counts=Counter()
    findings=[]
    for case_id,gold,admitted in rows:
        if (not isinstance(case_id,str) or not case_id or case_id in seen
                or gold not in LABELS or type(admitted) is not bool):
            raise ValueError("INVALID_SEMANTIC_EVALUATION_ROW")
        seen.add(case_id)
        counts["total"]+=1
        if gold=="SUPPORTED":
            counts["supported"]+=1
            if admitted: counts["supported_admitted"]+=1
            else: counts["supported_rejected"]+=1
        elif gold=="UNSUPPORTED":
            counts["unsupported"]+=1
            if admitted:
                counts["unsupported_admitted"]+=1
                findings.append({"case_id":case_id,
                                 "finding":"UNSUPPORTED_CLAIM_ADMITTED"})
            else: counts["unsupported_rejected"]+=1
        else:
            counts["abstention"]+=1
            if admitted: counts["abstention_admitted"]+=1
            else:
                counts["abstention_rejected"]+=1
                findings.append({"case_id":case_id,
                                 "finding":"SAFE_ABSTENTION_REJECTED"})
    if not seen:
        raise ValueError("EMPTY_SEMANTIC_EVALUATION")
    return {
        "evaluation_type":"DEVELOPER_LABELED_SYNTHETIC_OFFLINE",
        "case_count":counts["total"],
        "supported_count":counts["supported"],
        "supported_admitted":counts["supported_admitted"],
        "supported_rejected":counts["supported_rejected"],
        "unsupported_count":counts["unsupported"],
        "unsupported_admitted":counts["unsupported_admitted"],
        "unsupported_rejected":counts["unsupported_rejected"],
        "abstention_count":counts["abstention"],
        "abstention_admitted":counts["abstention_admitted"],
        "abstention_rejected":counts["abstention_rejected"],
        "unsupported_false_accept_rate":(
            counts["unsupported_admitted"]/counts["unsupported"]
            if counts["unsupported"] else None),
        "admission":"STOP" if (
            not counts["supported"] or not counts["unsupported"]
            or not counts["abstention"] or counts["unsupported_admitted"]>0
            or counts["supported_rejected"]>0
            or counts["abstention_rejected"]>0) else "CANDIDATE_ONLY",
        "findings":findings,
        "limitations":[
            "Developer-labeled synthetic cases, not independently adjudicated",
            "Measures output contract admission; does not measure model generations",
            "CANDIDATE_ONLY never authorizes real-model deployment",
        ],
    }
