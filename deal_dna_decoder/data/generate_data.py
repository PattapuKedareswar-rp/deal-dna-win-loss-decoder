"""Generate SYNTHETIC sales-call transcripts + Salesforce outcome map + reference taxonomies.

Deterministic (seeded). Produces speaker-attributed, timestamped transcripts with realistic,
extractable buying signals. This is NOT real customer data.

Run:  python data/generate_data.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent
T = DATA / "transcripts"
SF = DATA / "salesforce"
REF = DATA / "reference"
GOLD = DATA / "gold"
FIX = DATA / "fixtures"

COMPETITORS = ["Yardi", "Entrata", "MRI Software", "ResMan", "AppFolio"]
PRODUCTS = ["AI Revenue Management", "Resident Screening", "Payments & Billing",
            "Property Management Platform", "Leasing & Marketing"]


def ts(sec: int) -> str:
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def line(sec: int, role: str, name: str, text: str) -> str:
    return f"[{ts(sec)}] {role} - {name}: {text}"


# Each cycle: id, opp, account, product, competitor, owner, outcome, stage, close_date, calls[list of lines]
CYCLES: list[dict] = [
    {
        "cycle_id": "cyc-001", "opp": "006A001", "account": "Cedar Ridge Residential",
        "product": "AI Revenue Management", "competitor": "Entrata", "owner": "A. Morgan",
        "outcome": "Lost", "stage": "Closed Lost", "close_date": "2026-08-14",
        "calls": [
            [
                line(5, "Rep", "A. Morgan", "Thanks for the time. Where are you feeling the most pain today?"),
                line(48, "Buyer", "VP Operations", "Our team still sets renewals manually and it's painful across the portfolio."),
                line(126, "Buyer", "VP Operations", "We're also evaluating Entrata, who's our incumbent on a couple of sites."),
                line(205, "Rep", "A. Morgan", "Understood. Our AI revenue management automates that rent optimization."),
            ],
            [
                line(12, "Rep", "A. Morgan", "Any reaction to the demo we sent over?"),
                line(75, "Buyer", "CFO", "The revenue lift looked good, but once you add implementation fees the total cost is too high."),
                line(160, "Buyer", "CFO", "Honestly your list price is about 20% above the other bid and finance won't approve that budget."),
                line(240, "Buyer", "VP Operations", "We're also worried about the migration and onboarding timeline."),
                line(300, "Buyer", "CFO", "Entrata offered a multi-year lock-in discount to keep us."),
            ],
        ],
    },
    {
        "cycle_id": "cyc-002", "opp": "006A002", "account": "Harbor Point Communities",
        "product": "Property Management Platform", "competitor": "AppFolio", "owner": "F. Okafor",
        "outcome": "Won", "stage": "Closed Won", "close_date": "2026-07-30",
        "calls": [
            [
                line(8, "Rep", "F. Okafor", "What outcome would make this a win for your team?"),
                line(60, "Buyer", "Director of Ops", "We want to consolidate four point tools onto one platform."),
                line(140, "Buyer", "Director of Ops", "The demo really showed how the automation removes manual steps for our staff."),
            ],
            [
                line(15, "Rep", "F. Okafor", "Your CFO joined — want to talk value?"),
                line(70, "Buyer", "CFO", "The NOI improvement and revenue lift are compelling; the ROI payback is under a year."),
                line(150, "Buyer", "CFO", "Your peer references in our region were strong and built trust."),
                line(220, "Buyer", "Director of Ops", "The implementation plan de-risked the migration for us."),
            ],
        ],
    },
    {
        "cycle_id": "cyc-003", "opp": "006A003", "account": "Summit Valley Homes",
        "product": "Leasing & Marketing", "competitor": "None", "owner": "B. Chen",
        "outcome": "Stalled / No Decision", "stage": "Negotiation", "close_date": "",
        "calls": [
            [
                line(10, "Rep", "B. Chen", "Where are you in the decision process?"),
                line(65, "Buyer", "Marketing Lead", "We like the product, but our budget froze after a portfolio acquisition."),
                line(150, "Buyer", "Marketing Lead", "Timing is tough — we'd revisit next fiscal year."),
                line(210, "Buyer", "VP Marketing", "The CFO will need to approve this once budget reopens."),
            ],
        ],
    },
    {
        "cycle_id": "cyc-004", "opp": "006A004", "account": "Lakeside Living Group",
        "product": "Payments & Billing", "competitor": "Yardi", "owner": "C. Diaz",
        "outcome": "Lost", "stage": "Closed Lost", "close_date": "2026-08-02",
        "calls": [
            [
                line(9, "Rep", "C. Diaz", "What's driving the evaluation?"),
                line(58, "Buyer", "Controller", "We need an open API to our data warehouse and that seems to be on your roadmap still."),
                line(132, "Buyer", "Controller", "Yardi bundled the payments module for free to retain the account."),
                line(198, "Buyer", "Controller", "There's real switching cost risk and my team is hesitant."),
            ],
        ],
    },
    {
        "cycle_id": "cyc-005", "opp": "006A005", "account": "Northgate Property Partners",
        "product": "Resident Screening", "competitor": "MRI Software", "owner": "E. Novak",
        "outcome": "Won", "stage": "Closed Won", "close_date": "2026-07-11",
        "calls": [
            [
                line(11, "Rep", "E. Novak", "What matters most in a screening vendor?"),
                line(64, "Buyer", "Leasing Director", "Trust and references — your peer references were strong."),
                line(139, "Buyer", "Leasing Director", "The demo was smooth and the workflow fit how we operate."),
                line(205, "Buyer", "Ops Manager", "The implementation and support plan reduced our risk concerns."),
            ],
        ],
    },
    {
        "cycle_id": "cyc-006", "opp": "006A006", "account": "Riverstone Realty",
        "product": "AI Revenue Management", "competitor": "Entrata", "owner": "D. Patel",
        "outcome": "Lost", "stage": "Closed Lost", "close_date": "2026-08-20",
        "calls": [
            [
                line(7, "Rep", "D. Patel", "How did the demo land with the team?"),
                line(52, "Buyer", "Revenue Manager", "The demo felt clunky when you switched screens; automated renewals weren't obvious."),
                line(128, "Buyer", "Revenue Manager", "A competitor demoed automated renewals end to end."),
                line(190, "Buyer", "VP Ops", "We have a missing feature gap for our student housing workflow."),
            ],
        ],
    },
    {
        "cycle_id": "cyc-007", "opp": "006A007", "account": "Beacon Hill Apartments",
        "product": "Property Management Platform", "competitor": "ResMan", "owner": "A. Morgan",
        "outcome": "Won", "stage": "Closed Won", "close_date": "2026-06-28",
        "calls": [
            [
                line(10, "Rep", "A. Morgan", "What's the consolidation goal?"),
                line(66, "Buyer", "COO", "Consolidate point tools; the ROI and revenue lift justified it to the CFO."),
                line(142, "Buyer", "COO", "Your references and trust story were better than ResMan's."),
            ],
        ],
    },
    {
        "cycle_id": "cyc-008", "opp": "006A008", "account": "Willow Creek Management",
        "product": "Payments & Billing", "competitor": "None", "owner": "B. Chen",
        "outcome": "Stalled / No Decision", "stage": "Proposal", "close_date": "",
        "calls": [
            [
                line(9, "Rep", "B. Chen", "Any blockers to a decision this quarter?"),
                line(61, "Buyer", "Finance Director", "Budget approval is uncertain this quarter; timing is the issue."),
                line(150, "Buyer", "Finance Director", "We'd need the CFO to approve before we move."),
            ],
        ],
    },
    {
        "cycle_id": "cyc-009", "opp": "006A009", "account": "Maplewood Residences",
        "product": "Leasing & Marketing", "competitor": "Yardi", "owner": "F. Okafor",
        "outcome": "Lost", "stage": "Closed Lost", "close_date": "2026-08-09",
        "calls": [
            [
                line(8, "Rep", "F. Okafor", "What's the main concern?"),
                line(55, "Buyer", "Marketing Director", "Lost on total cost of ownership once implementation fees were added."),
                line(120, "Buyer", "Marketing Director", "Your price was too high versus the competing bid."),
            ],
        ],
    },
    {
        "cycle_id": "cyc-010", "opp": "006A010", "account": "Oakhaven Communities",
        "product": "AI Revenue Management", "competitor": "AppFolio", "owner": "D. Patel",
        "outcome": "Won", "stage": "Closed Won", "close_date": "2026-06-15",
        "calls": [
            [
                line(10, "Rep", "D. Patel", "What convinced the team?"),
                line(63, "Buyer", "CFO", "The AI revenue management pilot showed a clear rent-optimization lift."),
                line(138, "Buyer", "CFO", "Strong ROI and the CFO championed it internally."),
            ],
        ],
    },
    {
        "cycle_id": "cyc-011", "opp": "006A011", "account": "Prairie Winds Housing",
        "product": "Resident Screening", "competitor": "Entrata", "owner": "C. Diaz",
        "outcome": "Lost", "stage": "Closed Lost", "close_date": "2026-08-25",
        "calls": [
            [
                line(9, "Rep", "C. Diaz", "How are you weighing options?"),
                line(58, "Buyer", "Compliance Lead", "Reference checks raised onboarding and implementation risk concerns."),
                line(130, "Buyer", "Compliance Lead", "We're also talking to Entrata about the same scope."),
            ],
        ],
    },
    {
        "cycle_id": "cyc-012", "opp": "006A012", "account": "Fair Meadow Realty",
        "product": "Property Management Platform", "competitor": "None", "owner": "E. Novak",
        "outcome": "Won", "stage": "Closed Won", "close_date": "2026-07-05",
        "calls": [
            [
                line(11, "Rep", "E. Novak", "What made this the right fit?"),
                line(64, "Buyer", "Operations VP", "The platform fit and product consolidation removed manual work."),
                line(140, "Buyer", "Operations VP", "The demo and the implementation plan built confidence."),
            ],
        ],
    },
    {
        "cycle_id": "cyc-013", "opp": "006A013", "account": "Copperfield Communities",
        "product": "AI Revenue Management", "competitor": "ResMan", "owner": "F. Okafor",
        "outcome": "Won", "stage": "Closed Won", "close_date": "2026-06-02",
        "calls": [
            [
                line(9, "Rep", "F. Okafor", "What's the goal for this evaluation?"),
                line(58, "Buyer", "Revenue Manager", "We want to consolidate our point tools and cut the manual renewal work."),
                line(130, "Buyer", "Revenue Manager", "The demo really showed how the automation removes those manual steps."),
            ],
            [
                line(12, "Rep", "F. Okafor", "Your CFO is here today — shall we talk value?"),
                line(70, "Buyer", "CFO", "The ROI and revenue lift were compelling and the payback is under a year."),
                line(150, "Buyer", "CFO", "Your peer references in our region built real trust with the board."),
            ],
            [
                line(10, "Rep", "F. Okafor", "Any last concerns before we move forward?"),
                line(66, "Buyer", "Ops Director", "The implementation plan de-risked the migration for our team."),
                line(120, "Buyer", "Ops Director", "That reassured us on the onboarding risk."),
            ],
        ],
    },
    {
        "cycle_id": "cyc-014", "opp": "006A014", "account": "Stonebrook Rentals",
        "product": "Resident Screening", "competitor": "Yardi", "owner": "A. Morgan",
        "outcome": "Won", "stage": "Closed Won", "close_date": "2026-05-20",
        "calls": [
            [
                line(10, "Rep", "A. Morgan", "How did you land on a direction?"),
                line(62, "Buyer", "Leasing Director", "We had also been evaluating Yardi, but your revenue lift and ROI stood out."),
                line(135, "Buyer", "Leasing Director", "Strong peer references sealed the trust for us."),
            ],
        ],
    },
    {
        "cycle_id": "cyc-015", "opp": "006A015", "account": "Ironwood Property Group",
        "product": "Payments & Billing", "competitor": "Entrata", "owner": "C. Diaz",
        "outcome": "Lost", "stage": "Closed Lost", "close_date": "2026-08-28",
        "consent": "pending",  # exercises the intake gate -> Needs Review
        "calls": [
            [
                line(9, "Rep", "C. Diaz", "What drove the decision?"),
                line(60, "Buyer", "Controller", "Your price was too high once implementation fees were added."),
            ],
        ],
    },
    {
        "cycle_id": "cyc-016", "opp": "006A016", "account": "Brightwater Homes",
        "product": "Leasing & Marketing", "competitor": "None", "owner": "B. Chen",
        "outcome": "Won", "stage": "Closed Won", "close_date": "2026-05-05",
        "transcript_status": "Speaker attribution incomplete",  # exercises the intake gate
        "calls": [
            [
                line(11, "Rep", "B. Chen", "What convinced the team?"),
                line(64, "Buyer", "Marketing Lead", "The product fit and consolidation were the deciding factors."),
            ],
        ],
    },
    {
        "cycle_id": "cyc-017", "opp": "006A017", "account": "Sagebrush Living",
        "product": "Property Management Platform", "competitor": "Entrata", "owner": "D. Patel",
        "outcome": "Lost", "stage": "Closed Lost", "close_date": "2026-08-30",
        "calls": [
            [
                line(8, "Rep", "D. Patel", "How did the demo go with the wider team?"),
                line(55, "Buyer", "Ops Manager", "The demo felt clunky when you switched screens and lost the room."),
                line(120, "Buyer", "Ops Manager", "Automated renewals weren't obvious — it looked like a missing feature."),
            ],
        ],
    },
    {
        "cycle_id": "cyc-018", "opp": "006A018", "account": "Half Moon Residences",
        "product": "Property Management Platform", "competitor": "None", "owner": "E. Novak",
        "outcome": "Won", "stage": "Closed Won", "close_date": "2026-04-22",
        "calls": [
            [
                line(10, "Rep", "E. Novak", "What was the driver?"),
                line(63, "Buyer", "COO", "Consolidating four point tools onto one platform removed manual work."),
                line(138, "Buyer", "COO", "The implementation and support plan reduced our risk concerns."),
            ],
        ],
    },
]


def write_transcripts_and_manifest() -> list[dict]:
    manifest_rows: list[dict] = []
    for c in CYCLES:
        cdir = T / c["cycle_id"]
        cdir.mkdir(parents=True, exist_ok=True)
        for i, call_lines in enumerate(c["calls"], start=1):
            call_id = f"call-{i}"
            txt = cdir / f"{call_id}.txt"
            txt.write_text("\n".join(call_lines) + "\n", encoding="utf-8")
            meta = {
                "cycle_id": c["cycle_id"], "call_id": call_id,
                "opportunity_id": c["opp"], "account": c["account"],
                "call_date": c["close_date"] or "2026-08-01",
                "source_system": "SYNTHETIC demo (fallback)",
                "product": c["product"], "stage": c["stage"],
                "consent": c.get("consent", "approved"),
                "transcript_status": c.get("transcript_status", "Full transcript available"),
            }
            (cdir / f"{call_id}.metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
            manifest_rows.append({
                "cycle_id": c["cycle_id"], "call_id": call_id,
                "source": str(txt.relative_to(DATA.parent)),
                "outcome": c["outcome"],
                "completeness": c.get("transcript_status", "Full transcript available"),
                "consent": c.get("consent", "approved"),
            })
    return manifest_rows


def write_salesforce() -> None:
    SF.mkdir(parents=True, exist_ok=True)
    with (SF / "opportunities.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["opportunity_id", "account", "product_family", "stage", "IsWon",
                    "outcome", "owner", "close_date", "sale_type"])
        for c in CYCLES:
            is_won = "true" if c["outcome"] == "Won" else "false"
            w.writerow([c["opp"], c["account"], c["product"], c["stage"], is_won,
                        c["outcome"], c["owner"], c["close_date"], "New"])


def write_reference() -> None:
    REF.mkdir(parents=True, exist_ok=True)
    (REF / "competitor-taxonomy.yaml").write_text(
        "competitors:\n" + "".join(f"  - {x}\n" for x in COMPETITORS), encoding="utf-8")
    (REF / "product-taxonomy.yaml").write_text(
        "products:\n" + "".join(f"  - {x}\n" for x in PRODUCTS), encoding="utf-8")
    (REF / "theme-taxonomy.yaml").write_text(
        "themes:\n" + "".join(f"  - {x}\n" for x in
        ["need", "pricing", "demo", "roi", "competitor", "integration",
         "trust", "timing", "authority", "risk", "implementation", "product"]),
        encoding="utf-8")


def write_manifest(rows: list[dict]) -> None:
    with (DATA / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["cycle_id", "call_id", "source", "outcome",
                                          "completeness", "consent"])
        w.writeheader()
        w.writerows(rows)


def write_gold() -> None:
    GOLD.mkdir(parents=True, exist_ok=True)
    gold = [
        ("cyc-001", "Lost", "pricing", "Price/TCO too high vs incumbent discount"),
        ("cyc-002", "Won", "roi", "Consolidation + ROI + strong references"),
        ("cyc-003", "Stalled / No Decision", "timing", "Budget froze after acquisition"),
        ("cyc-004", "Lost", "integration", "Open-API gap; incumbent bundling"),
        ("cyc-006", "Lost", "demo", "Demo friction; missing automated renewals"),
        ("cyc-013", "Won", "roi", "Multi-call: ROI + references + de-risked implementation"),
        ("cyc-017", "Lost", "demo", "Demo friction lost the room; renewals gap"),
    ]
    with (GOLD / "human-reviewed-labels.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["cycle_id", "outcome", "top_driver_category", "human_note"])
        w.writerows(gold)


def main() -> None:
    for d in (T, SF, REF, GOLD, FIX):
        d.mkdir(parents=True, exist_ok=True)
    rows = write_transcripts_and_manifest()
    write_salesforce()
    write_reference()
    write_manifest(rows)
    write_gold()
    print(f"Generated {len(CYCLES)} synthetic cycles, {len(rows)} calls.")
    print(f"Transcripts: {T}")
    print(f"Salesforce map: {SF / 'opportunities.csv'}")


if __name__ == "__main__":
    main()
