"""One-shot script to generate a few sample PDF clinic docs with reportlab."""

from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

OUT = Path(__file__).resolve().parent.parent / "docs"

DOCS = [
    (
        "21_sterilization_protocol.pdf",
        "Sterilization and Infection Control",
        [
            "BrightSmile follows CDC guidelines for infection control.",
            "All reusable instruments are cleaned, packaged, and autoclaved.",
            "Biological spore testing of sterilizers is performed weekly.",
            "Single-use items (needles, gloves, suction tips) are never reused.",
            "Operatories are disinfected between patients with hospital-grade surface disinfectant.",
            "Staff complete annual infection-control training and hepatitis B vaccination verification.",
        ],
    ),
    (
        "22_radiograph_policy.pdf",
        "Dental X-Ray Policy",
        [
            "We use digital radiography to minimize radiation exposure.",
            "Bitewing X-rays are typically taken once per year for adults with low cavity risk.",
            "A full-mouth series or panoramic image is taken every 3–5 years, or sooner if clinically needed.",
            "Lead aprons and thyroid collars are available; digital sensors already reduce dose substantially.",
            "Pregnant patients: elective X-rays are deferred when possible; urgent diagnostic images use shielding.",
            "You may decline X-rays, but diagnosis and treatment planning may be limited without them.",
        ],
    ),
    (
        "23_referral_network.pdf",
        "Specialist Referral Network",
        [
            "When care is outside our scope, we refer to trusted specialists.",
            "Orthodontics: Riverside Orthodontic Group (braces and clear aligners).",
            "Complex oral surgery / impacted wisdom teeth: Valley Oral Surgery Associates.",
            "Endodontics (difficult root canals): Canal Care Endodontics.",
            "Periodontics (advanced gum surgery / grafts): Riverside Perio Center.",
            "We send records and X-rays electronically with your signed release. Follow-up returns to BrightSmile for routine care unless otherwise noted.",
        ],
    ),
]


def write_pdf(filename, title, lines):
    path = OUT / filename
    c = canvas.Canvas(str(path), pagesize=letter)
    width, height = letter
    y = height - 72
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, y, title)
    y -= 36
    c.setFont("Helvetica", 11)
    for line in lines:
        # wrap roughly at 90 chars
        words = line.split()
        row = ""
        for w in words:
            trial = (row + " " + w).strip()
            if len(trial) > 90:
                c.drawString(72, y, row)
                y -= 18
                row = w
                if y < 72:
                    c.showPage()
                    c.setFont("Helvetica", 11)
                    y = height - 72
            else:
                row = trial
        if row:
            c.drawString(72, y, row)
            y -= 22
            if y < 72:
                c.showPage()
                c.setFont("Helvetica", 11)
                y = height - 72
    c.save()
    print(f"wrote {path}")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for filename, title, lines in DOCS:
        write_pdf(filename, title, lines)
