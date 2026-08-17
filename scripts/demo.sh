#!/usr/bin/env bash
# Hamroh — diabet demo ssenariysi, terminaldan mashq qilish uchun.
# Server allaqachon ishlab turishi kerak (./scripts/run.sh).
#
# Usage:  ./scripts/demo.sh [base_url]
#         ./scripts/demo.sh http://localhost:5001

set -euo pipefail

BASE="${1:-${BASE:-http://localhost:5000}}"
PATIENT_ID="${PATIENT_ID:-1}"

say()  { printf '\n\033[0;36m==> %s\033[0m\n' "$1"; }
step() { printf '    %s\n' "$1"; }

command -v curl >/dev/null 2>&1 || { echo "curl kerak: sudo apt install -y curl" >&2; exit 1; }

if ! curl -sf "$BASE/health" >/dev/null; then
  printf '\033[0;31mXATO:\033[0m %s javob bermayapti. Avval serverni ishga tushiring:\n' "$BASE" >&2
  printf '       ./scripts/run.sh\n' >&2
  exit 1
fi

post() { curl -sf -X POST "$BASE$1" -H 'Content-Type: application/json' -d "$2"; }

say "1/6  Demo boshiga qaytarilmoqda"
post "/api/v1/demo/reset" '{}' >/dev/null
step "barcha bemorlar: 0-kun, yashil"

say "2/6  1-kun — nahorgi qand me'yorda"
post "/api/v1/demo/advance-day" "{\"patient_id\":$PATIENT_ID}" >/dev/null
post "/api/v1/patients/$PATIENT_ID/messages" '{"text":"6.4"}' >/dev/null
step "kutilgan natija: YASHIL — maqsad < 7.0 mmol/l"

say "3/6  2-kun — qon bosimi maqsaddan yuqori"
post "/api/v1/demo/advance-day" "{\"patient_id\":$PATIENT_ID}" >/dev/null
post "/api/v1/patients/$PATIENT_ID/messages" '{"text":"142/88"}' >/dev/null
step "kutilgan natija: SARIQ — 18-65 yosh uchun maqsad <= 130/80"

say "4/6  3-kun — ovqatdan keyingi qand yuqori"
post "/api/v1/demo/advance-day" "{\"patient_id\":$PATIENT_ID}" >/dev/null
post "/api/v1/patients/$PATIENT_ID/messages" '{"text":"12.8"}' >/dev/null
step "kutilgan natija: SARIQ — maqsad < 10.0 mmol/l"

say "5/6  4-kun — KETOATSIDOZ belgilari"
post "/api/v1/demo/advance-day" "{\"patient_id\":$PATIENT_ID}" >/dev/null
post "/api/v1/patients/$PATIENT_ID/messages" \
     '{"text":"Ogzim quruq, nafasimdan galati hid kelyapti, qustim. Qand 18.2"}' >/dev/null
step "kutilgan natija: QIZIL — aseton hidi + qusish + giperglikemiya"
step "protokol: shoshilinch kasalxonaga yotqizish, ambulator davolash taqiqlanadi"

say "6/6  Shifokor javob yozmoqda"
post "/api/v1/patients/$PATIENT_ID/doctor-message" \
     '{"text":"Bobur aka, zudlik bilan 103 ga qongiroq qiling yoki eng yaqin shifoxonaga boring."}' >/dev/null
step "bemor chatida darhol ko'rinadi"

say "Holat"
curl -sf "$BASE/api/v1/doctors/1/dashboard" \
  | python3 -c 'import json,sys; d=json.load(sys.stdin)["data"]; print("    hisob:", d["counts"]); [print("    %-20s %s" % (p["full_name"], p["risk_level"])) for p in d["patients"]]'

cat <<EOF

  Brauzerda ko'ring:
    Panel      $BASE/doctor/1/dashboard
    Bemor chat $BASE/patient/$PATIENT_ID/chat
    Tafsilot   $BASE/doctor/patient/$PATIENT_ID

  Qo'lda sinash uchun boshqa jumlalar:

    GIPOGLIKEMIYA (teri nam, tez rivojlanadi):
      "terlayapman, qollarim titrayapti, juda och qoldim"
      yoki qand qiymati: 3.2

    INSULIN UZILISHI (DKA ning eng kop uchraydigan sababi):
      "kecha insulinimni qilmadim, tugab qolgan edi"

    NEFROPATIYA:
      "oyoqlarim shishgan, siydigim kamaydi"

    NEYROPATIYA:
      "oyoqlarim uvishyapti, korishim xiralashdi"

EOF
