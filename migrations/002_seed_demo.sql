-- 002_seed_demo.sql — demo data: one doctor, patient Bobur, 5 days of check-in
-- questions. Adding a persona or a question later means a NEW seed migration,
-- never a Python change (PLAN.md principle 1).
-- Note: apostrophes in Uzbek words are escaped as '' inside SQL literals.

INSERT INTO doctors (full_name, clinic_name, phone_sim) VALUES
    ('Dilnoza Karimova', 'Qarshi shahar 3-son OSHP', '+998 90 123 45 67');

INSERT INTO patients (
    full_name, persona_key, diagnosis, discharge_date, phone_sim,
    doctor_id, current_day, risk_level, meta_json
) VALUES (
    'Bobur Ergashev',
    'bobur',
    'O''tkir appenditsit — laparoskopik appendektomiya',
    date('now'),
    '+998 91 234 56 78',
    (SELECT id FROM doctors WHERE full_name = 'Dilnoza Karimova'),
    0,
    'green',
    '{"age": 34, "surgery": "appendektomiya", "language": "uz"}'
);

-- Five days of follow-up questions for the "bobur" persona.
-- seq = 0 everywhere for now; the column is ready for several questions a day.
INSERT INTO checkin_templates
    (persona_key, day_offset, seq, question_key, question_text, answer_type, config_json)
VALUES
    ('bobur', 1, 0, 'temperature',
     'Assalomu alaykum, Bobur! Operatsiyadan keyingi 1-kun. Bugun tana haroratingiz necha daraja? Masalan: 36.8',
     'number',
     '{"unit": "°C", "min": 34, "max": 43, "placeholder": "36.8"}'),

    ('bobur', 2, 0, 'pain',
     'Xayrli kun, Bobur! 2-kun. Jarohat sohasidagi og''riqni 1 dan 10 gacha baholang: 1 — deyarli yo''q, 10 — juda kuchli.',
     'scale_1_10',
     '{"min": 1, "max": 10}'),

    ('bobur', 3, 0, 'wound',
     'Salom, Bobur! 3-kun. Jarohat holati qanday? Qizarish, shish yoki yiring bormi? Bog''lam quruqmi?',
     'free_text',
     '{"placeholder": "Masalan: bog''lam quruq, qizarish yo''q"}'),

    ('bobur', 4, 0, 'mobility',
     'Salom, Bobur! 4-kun. Bugun o''rningizdan turib yura oldingizmi? Qancha vaqt yurdingiz?',
     'free_text',
     '{"placeholder": "Masalan: kuniga 3 marta, 10 daqiqadan"}'),

    ('bobur', 5, 0, 'wellbeing',
     'Salom, Bobur! 5-kun. Umumiy ahvolingiz qanday? Ishtaha, uyqu va kayfiyatingiz haqida yozing.',
     'free_text',
     '{"placeholder": "Masalan: ishtaha yaxshi, uyqu tinch"}');
