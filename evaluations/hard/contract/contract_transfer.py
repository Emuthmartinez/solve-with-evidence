"""Prospective transfer test for delivery of a declarative routing policy."""
import itertools
import json

CASE = "contract-h4"
FIELDS = {"wear": ("worn", "sound"), "carrier": ("wax", "film", "disc"), "marked": (False, True)}
BINS = ("stabilize", "cold", "digitize", "shelf", "exhibit")
STAGE1 = """A sound archive routes recordings into work queues. Deliver a runnable JSON decision table for its sorter. A valid input is an object with the single key "request". The value of "request" is an object with exactly three fields: "wear" is "worn" or "sound", "carrier" is "wax", "film", or "disc", and "marked" is a JSON boolean. A worn recording always goes to "stabilize". Among sound recordings, wax goes to "cold", marked non-wax goes to "digitize", and the rest go to "shelf"."""
STAGE2 = """An exhibit now reserves certain recordings. A request may include a fourth field "campaign", a JSON boolean that defaults to false when absent. Only sound, marked discs with campaign true go to the new queue "exhibit". All other inputs keep the previous behavior. Deliver the entire updated decision table, including support for every original three-field input. Rows may also match "campaign" in this version."""
FORMAT = """The sorter consumes "table", an ordered JSON array of rows. Each row must contain exactly {"when":{...},"bin":"..."}. The keys inside "when" are zero or more field names from the inner request object. Each value must be one legal scalar value of that field. The sorter chooses the bin of the first row for which every field in "when" equals its requested value. An empty "when" matches any input. The table must route all valid inputs. Use only queue names introduced so far.

Return only a JSON object with exactly the keys "table", "routed", and "witness". "routed" is the array of correct queue names for the supplied inputs, in order. "witness" is a separate example with exactly two keys: "input", containing one complete valid input object with its outer "request" key, and "expected", containing its correct queue name. Choose any valid input on which the faulty sorter below disagrees with the correct sorter. The witness can be different from all supplied inputs."""
FAULT = ("The faulty sorter sends every wax recording to cold before considering wear; it agrees on everything else.",
         "The faulty sorter sends every sound, marked recording with campaign true to exhibit, regardless of carrier; it agrees on everything else.")


def envelope(wear, carrier, marked, campaign=None):
    fields = {"wear": wear, "carrier": carrier, "marked": marked}
    if campaign is not None:
        fields["campaign"] = campaign
    return {"request": fields}


def samples(stage):
    if stage == 1:
        return [envelope("sound","wax",True), envelope("worn","film",False),
                envelope("sound","disc",True), envelope("sound","film",False)]
    return [envelope("sound","disc",True,True), envelope("sound","wax",False,True),
            envelope("worn","disc",True,True), envelope("sound","disc",True),
            envelope("sound","disc",False,False)]


def prompt(case, stage):
    if case != CASE or stage not in (1, 2):
        raise ValueError("unknown case or stage")
    return "\n\n".join([STAGE1 if stage == 1 else STAGE2, FORMAT, FAULT[stage-1],
                       "Supplied inputs (JSON): " + json.dumps(samples(stage), separators=(",",":"))])


def reference(item, stage, faulty=False):
    rec = item["request"]
    if stage == 1 and faulty and rec["carrier"] == "wax":
        return "cold"
    if rec["wear"] == "worn":
        return "stabilize"
    if stage == 2 and rec.get("campaign",False) and rec["marked"] and (faulty or rec["carrier"] == "disc"):
        return "exhibit"
    if rec["carrier"] == "wax":
        return "cold"
    return "digitize" if rec["marked"] else "shelf"


def allowed(stage):
    return FIELDS if stage == 1 else {**FIELDS, "campaign": (False,True)}


def valid_values(fields, stage):
    legal = allowed(stage)
    return isinstance(fields, dict) and all(
        k in legal and any(type(v) is type(x) and v == x for x in legal[k]) for k,v in fields.items())


def valid_table(tab, stage):
    return isinstance(tab,list) and all(
        isinstance(row,dict) and set(row) == {"when","bin"} and valid_values(row["when"],stage)
        and row["bin"] in BINS[:4 if stage == 1 else 5] for row in tab)


def evaluate(table, item):
    rec = {"campaign":False, **item["request"]}
    for row in table:
        if all(rec[k] == v for k,v in row["when"].items()):
            return row["bin"]
    return None


def valid_input(obj, stage):
    if not isinstance(obj,dict) or set(obj) != {"request"}:
        return False
    rec = obj["request"]
    return valid_values(rec,stage) and set(FIELDS) <= set(rec)


def cases(stage):
    campaigns = (None,) if stage == 1 else (None,False,True)
    return [envelope(*x) for x in itertools.product(*FIELDS.values(),campaigns)]


def grade(case, replies):
    if case != CASE:
        raise ValueError("unknown case")
    checks = {}
    executed = {}
    for stage in (1,2):
        ans = replies[stage-1] if stage <= len(replies) and isinstance(replies[stage-1],dict) else {}
        tab = ans.get("table")
        syntax = valid_table(tab,stage)
        domain = cases(stage)
        diff = [item for item in domain if not syntax or evaluate(tab,item) != reference(item,stage)]
        proof = ans.get("witness")
        form = isinstance(proof,dict) and set(proof) == {"input","expected"} and valid_input(proof["input"],stage)
        correct = form and proof["expected"] == reference(proof["input"],stage)
        detects = correct and reference(proof["input"],stage) != reference(proof["input"],stage,True)
        criteria = {
            "deliverable_shape": set(ans) == {"table","routed","witness"},
            "table_syntax": syntax,
            "all_original_inputs": not any("campaign" not in obj["request"] for obj in diff),
            "supplied_outputs": ans.get("routed") == [reference(item,stage) for item in samples(stage)],
            "witness_shape": form, "witness_expected": correct, "witness_distinguishes": detects,
        }
        if stage == 2:
            for mode in (False,True):
                criteria["explicit_campaign_"+str(mode).lower()] = not any(
                    obj["request"].get("campaign") is mode for obj in diff)
        for name,result in criteria.items():
            checks[f"stage{stage}_{name}"] = {"passed": bool(result),"weight":1}
        executed[str(stage)] = {"matched":len(domain)-len(diff),"valid_inputs":len(domain)}
    failed = [k for k,v in checks.items() if not v["passed"]]
    return {"case":case,"points":len(checks)-len(failed),"max_points":len(checks),
            "pass":not failed,"checks":checks,"critical_failures":failed,"execution":executed}


def decode(text):
    def pairs(rows):
        obj = dict(rows)
        if len(rows) != len(obj):
            raise ValueError("duplicate key")
        return obj
    try:
        obj = json.loads(text,object_pairs_hook=pairs)
        return obj if isinstance(obj,dict) else {}
    except (ValueError, TypeError):
        return {}
