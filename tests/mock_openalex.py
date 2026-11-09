"""Offline stand-in for the OpenAlex API, used only to test the pipeline. SYNTHETIC numbers.

    python tests/mock_openalex.py 8766
    OPENALEX_BASE=http://127.0.0.1:8766 python run_all.py
"""
import json
import math
import random
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

random.seed(3)
FIELDS = {"17": "Computer Science", "27": "Medicine", "22": "Engineering", "13": "Biochemistry, Genetics and Molecular Biology",
          "23": "Environmental Science", "33": "Social Sciences", "26": "Mathematics", "31": "Physics and Astronomy"}
DOMAIN = {"17": "3", "22": "3", "26": "3", "31": "3", "23": "3", "27": "4", "13": "1", "33": "2"}
SUBS = {  # id: (name, field, base works 2015, annual growth)
    "1702": ("Artificial Intelligence", "17", 60000, 0.17), "1707": ("Computer Vision and Pattern Recognition", "17", 40000, 0.12),
    "1705": ("Computer Networks and Communications", "17", 50000, 0.01), "1710": ("Information Systems", "17", 30000, 0.03),
    "2713": ("Epidemiology", "27", 45000, 0.06), "2740": ("Pulmonary and Respiratory Medicine", "27", 30000, 0.05),
    "2746": ("Surgery", "27", 90000, 0.02), "2730": ("Oncology", "27", 110000, 0.04),
    "2208": ("Electrical and Electronic Engineering", "22", 120000, 0.03), "2207": ("Control and Systems Engineering", "22", 50000, 0.05),
    "1312": ("Molecular Biology", "13", 100000, 0.01), "1311": ("Genetics", "13", 60000, 0.00),
    "2310": ("Pollution", "23", 25000, 0.10), "2306": ("Global and Planetary Change", "23", 20000, 0.09),
    "3304": ("Education", "33", 70000, 0.06), "3312": ("Sociology and Political Science", "33", 40000, 0.01),
    "2604": ("Applied Mathematics", "26", 50000, -0.01), "2610": ("Mathematical Physics", "26", 15000, -0.03),
    "3107": ("Atomic and Molecular Physics, and Optics", "31", 55000, 0.00), "3104": ("Condensed Matter Physics", "31", 60000, -0.01),
    "1708": ("Hardware and Architecture", "17", 400, 0.05),
}
YEARS = range(2015, 2027)
WORKS = {(s, y): int(b * (1 + g) ** (y - 2015) * random.uniform(0.95, 1.05)) for s, (_, _, b, g) in SUBS.items() for y in YEARS}
TOPICS = {s: [(f"T{s}{i}", f"{SUBS[s][0]} topic {chr(65 + i)}", random.uniform(-0.05, 0.25)) for i in range(6)] for s in SUBS}
COUNTRIES = [("US", "United States", 0.30, -0.01), ("CN", "China", 0.20, 0.06), ("GB", "United Kingdom", 0.08, 0.0),
             ("IN", "India", 0.06, 0.08), ("DE", "Germany", 0.07, -0.01), ("JP", "Japan", 0.05, -0.02)]
UNKNOWN_SHARE = 0.04


def overlap(a, b, y):
    if a == b:
        return 1.0
    base = 0.02 + 0.10 * ((int(a) * 7 + int(b) * 3) % 5) / 4
    if "17" in (a, b):
        base += 0.01 * (y - 2015)
    return min(base, 0.6)


def parse_filter(f):
    out = {}
    for part in f.split(","):
        k, v = part.split(":", 1)
        out[k] = v
    return out


def years_of(v):
    if "-" in v:
        a, b = v.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(v)]


def subs_matching(flt):
    s = list(SUBS)
    if "primary_topic.subfield.id" in flt:
        s = [x for x in s if x == flt["primary_topic.subfield.id"]]
    if "primary_topic.field.id" in flt:
        s = [x for x in s if SUBS[x][1] == flt["primary_topic.field.id"]]
    return s


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, obj):
        b = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-RateLimit-Remaining", "999")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        qs = {k: v[0] for k, v in parse_qs(u.query).items()}
        if u.path == "/subfields":
            if qs.get("page", "1") != "1":
                return self.send({"meta": {"count": len(SUBS)}, "results": []})
            return self.send({"meta": {"count": len(SUBS)}, "results": [
                {"id": f"https://openalex.org/subfields/{s}", "display_name": n,
                 "field": {"id": f"https://openalex.org/fields/{f}", "display_name": FIELDS[f]},
                 "domain": {"id": f"https://openalex.org/domains/{DOMAIN[f]}", "display_name": "Domain " + DOMAIN[f]}}
                for s, (n, f, _, _) in SUBS.items()]})
        if u.path == "/institutions":
            return self.send({"results": [{"id": "https://openalex.org/I123456789", "display_name": "University of North Texas"}]})
        if u.path != "/works":
            return self.send({})
        flt = parse_filter(qs.get("filter", ""))
        yrs = years_of(flt.get("publication_year", "2015-2026"))
        scale = 0.004 if "authorships.institutions.lineage" in flt else 1.0
        grp = qs.get("group_by")

        if "topics.subfield.id" in flt:  # focus subfield (any topic in it)
            fs = flt["topics.subfield.id"]
            total = sum(int(WORKS[(fs, y)] * 1.5) for y in yrs)
            if not grp:
                return self.send({"meta": {"count": total}, "results": []})
            own = SUBS[fs][1]
            groups = [{"key": f"https://openalex.org/fields/{f}", "key_display_name": FIELDS[f],
                       "count": total if f == own else int(total * overlap(own, f, yrs[0]) * 0.8)} for f in FIELDS]
            return self.send({"meta": {"count": total}, "group_by": groups})

        subs = subs_matching(flt)
        total = int(sum(WORKS[(s, y)] for s in subs for y in yrs) * scale)
        if not grp:
            return self.send({"meta": {"count": total}, "results": []})
        groups = []
        if grp.startswith("primary_topic.field.id"):
            for f in FIELDS:
                c = int(sum(WORKS[(s, y)] for s in subs if SUBS[s][1] == f for y in yrs) * scale)
                if c:
                    groups.append({"key": f"https://openalex.org/fields/{f}", "key_display_name": FIELDS[f], "count": c})
            if grp.endswith(":include_unknown"):
                groups.append({"key": "unknown", "key_display_name": "unknown", "count": int(total * UNKNOWN_SHARE)})
        elif grp == "publication_year":
            groups = [{"key": str(y), "key_display_name": str(y), "count": int(sum(WORKS[(s, y)] for s in subs) * scale)} for y in yrs]
        elif grp == "topics.field.id":
            pf = flt["primary_topic.field.id"]
            groups = [{"key": f"https://openalex.org/fields/{f}", "key_display_name": FIELDS[f],
                       "count": int(total * overlap(pf, f, yrs[0]))} for f in FIELDS]
        elif grp == "primary_topic.id":
            s = subs[0]
            mid = sum(yrs) / len(yrs)
            for tid, name, g in TOPICS[s]:
                groups.append({"key": f"https://openalex.org/{tid}", "key_display_name": name,
                               "count": int(total / 6 * (1 + g) ** (mid - 2020))})
        elif grp == "authorships.countries":
            for code, name, sh, g in COUNTRIES:
                groups.append({"key": f"https://openalex.org/countries/{code}", "key_display_name": name,
                               "count": int(total * sh * (1 + g) ** (yrs[0] - 2020))})
        return self.send({"meta": {"count": total, "groups_count": len(groups)}, "group_by": groups})


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1]) if len(sys.argv) > 1 else 8766), H).serve_forever()
