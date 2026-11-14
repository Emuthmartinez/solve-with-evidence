"""Independent hand-computed records, alternate table, and fault injections."""
from copy import deepcopy
import json
from contract_transfer import CASE, cases, decode, grade


def row(bin_name, **when):
    return {"when": when, "bin": bin_name}


def controls():
    tab = [row("stabilize",wear="worn"),row("cold",carrier="wax"),row("digitize",marked=True),row("shelf")]
    exhibit = row("exhibit",wear="sound",carrier="disc",marked=True,campaign=True)
    gold = [
        {"table": tab, "routed":["cold","stabilize","digitize","shelf"],
         "witness":{"input":{"request":{"wear":"worn","carrier":"wax","marked":False}},"expected":"stabilize"}},
        {"table":[exhibit,*tab],"routed":["exhibit","cold","stabilize","digitize","shelf"],
         "witness":{"input":{"request":{"wear":"sound","carrier":"film","marked":True,"campaign":True}},"expected":"digitize"}}
    ]
    def test(candidate, targets=()):
        g = grade(CASE,candidate)
        assert set(targets) <= set(g["critical_failures"])
        assert g["pass"] is (not targets)
    test(gold)
    alt = deepcopy(gold)
    # A legal table can enumerate categories, order disjoint rows freely, and omit a catch-all.
    for stage,ans in enumerate(alt,1):
        rows = []
        for obj in reversed(cases(stage)):
            fields = obj["request"]
            if stage == 2 and "campaign" not in fields:
                continue
            wear,carrier,marked = (fields[k] for k in ("wear","carrier","marked"))
            b = {"wax":"cold","film":"digitize" if marked else "shelf","disc":"digitize" if marked else "shelf"}[carrier]
            if stage == 2 and fields["campaign"] and marked and carrier == "disc":
                b="exhibit"
            rows.append(row("stabilize" if wear == "worn" else b,**fields))
        ans["table"] = rows
    test(alt)
    faults = {}
    def mutant(tag,index,key,value,checks):
        answer = deepcopy(gold)
        answer[index][key] = value
        test(answer,checks)
        faults[tag] = checks
    mutant("precedence",0,"table",[tab[1],tab[0],*tab[2:]],["stage1_all_original_inputs"])
    mutant("broadened exhibit",1,"table",[row("exhibit",wear="sound",marked=True,campaign=True),*tab],
           ["stage2_explicit_campaign_true"])
    mutant("lost absent-field rows",1,"table",[exhibit, *[{"bin":r["bin"],"when":{**r["when"],"campaign":True}} for r in tab]],
           ["stage2_all_original_inputs","stage2_explicit_campaign_false"])
    mutant("flattened input",0,"witness",{"input":gold[0]["witness"]["input"]["request"],"expected":"stabilize"},
           ["stage1_witness_shape"])
    mutant("valid but non-distinguishing",1,"witness",{"input":{"request":{"wear":"sound","marked":True,"carrier":"disc","campaign":True}},"expected":"exhibit"},
           ["stage2_witness_distinguishes"])
    mutant("wrong oracle result",0,"witness",{**gold[0]["witness"],"expected":"cold"},["stage1_witness_expected"])
    mutant("boolean confused with number",0,"table",[row("digitize",marked=1),*tab],["stage1_table_syntax"])
    mutant("wrong reported order",1,"routed",list(reversed(gold[1]["routed"])),["stage2_supplied_outputs"])
    for bad in ('[]','{"a":1,"a":2}','```json\n{}\n```'):
        assert decode(bad) == {}
    assert decode(json.dumps(gold[0])) == gold[0]
    return {"positive_controls":2,"negative_controls":faults,"parser_controls":4,"domain_counts":[len(cases(s)) for s in (1,2)]}

if __name__ == "__main__":
    print(json.dumps(controls(),indent=2))
