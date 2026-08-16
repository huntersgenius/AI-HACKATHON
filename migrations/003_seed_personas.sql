-- 003_seed_personas.sql — two more personas: Aziza (post-caesarean) and
-- Hasan (heart failure follow-up).
--
-- This migration is the architecture test from PLAN.md section 8: adding a
-- persona must be data only. No Python file is touched, and no analyzer,
-- service or route knows these names exist.
--
-- Note: apostrophes in Uzbek words are escaped as '' inside SQL literals.

INSERT INTO patients (
    full_name, persona_key, diagnosis, discharge_date, phone_sim,
    doctor_id, current_day, risk_level, meta_json
) VALUES
    ('Aziza Rahimova',
     'aziza',
     'Kesar kesish operatsiyasidan keyingi kuzatuv',
     date('now'),
     '+998 93 345 67 89',
     (SELECT id FROM doctors WHERE full_name = 'Dilnoza Karimova'),
     0,
     'green',
     '{"age": 28, "surgery": "kesar kesish", "language": "uz"}'),

    ('Hasan Yoʻldoshev',
     'hasan',
     'Yurak yetishmovchiligi — statsionardan keyingi kuzatuv',
     date('now'),
     '+998 94 456 78 90',
     (SELECT id FROM doctors WHERE full_name = 'Dilnoza Karimova'),
     0,
     'green',
     '{"age": 61, "condition": "yurak yetishmovchiligi", "language": "uz"}');

-- Aziza: five days after a caesarean section.
INSERT INTO checkin_templates
    (persona_key, day_offset, seq, question_key, question_text, answer_type, config_json)
VALUES
    ('aziza', 1, 0, 'temperature',
     'Assalomu alaykum, Aziza! Operatsiyadan keyingi 1-kun. Tana haroratingiz necha daraja? Masalan: 36.9',
     'number',
     '{"unit": "°C", "min": 34, "max": 43, "placeholder": "36.9"}'),

    ('aziza', 2, 0, 'bleeding',
     'Xayrli kun, Aziza! 2-kun. Qon ketishi qanday? Miqdori kamaydimi yoki ko''paydimi?',
     'free_text',
     '{"placeholder": "Masalan: kamaydi, rangi och"}'),

    ('aziza', 3, 0, 'wound',
     'Salom, Aziza! 3-kun. Chok holati qanday? Qizarish, shish yoki yiring bormi?',
     'free_text',
     '{"placeholder": "Masalan: chok toza, qizarish yo''q"}'),

    ('aziza', 4, 0, 'pain',
     'Salom, Aziza! 4-kun. Og''riqni 1 dan 10 gacha baholang: 1 — deyarli yo''q, 10 — juda kuchli.',
     'scale_1_10',
     '{"min": 1, "max": 10}'),

    ('aziza', 5, 0, 'wellbeing',
     'Salom, Aziza! 5-kun. Kayfiyatingiz qanday? Uyqu va ishtaha haqida yozing.',
     'free_text',
     '{"placeholder": "Masalan: uyqu tinch, ishtaha yaxshi"}');

-- Hasan: five days after a heart-failure admission.
INSERT INTO checkin_templates
    (persona_key, day_offset, seq, question_key, question_text, answer_type, config_json)
VALUES
    ('hasan', 1, 0, 'breathing',
     'Assalomu alaykum, Hasan! Kuzatuvning 1-kuni. Nafas olishingiz qanday? Yurganda hansiraysizmi?',
     'free_text',
     '{"placeholder": "Masalan: yurganda biroz hansirayman"}'),

    ('hasan', 2, 0, 'swelling',
     'Xayrli kun, Hasan! 2-kun. Oyoqlaringizda shish bormi? Kechga tomon kuchayadimi?',
     'free_text',
     '{"placeholder": "Masalan: to''piqda biroz shish bor"}'),

    ('hasan', 3, 0, 'medication',
     'Salom, Hasan! 3-kun. Bugun dorilarni belgilangan vaqtda qabul qildingizmi?',
     'yes_no',
     '{"options": ["ha", "yo''q"]}'),

    ('hasan', 4, 0, 'pain',
     'Salom, Hasan! 4-kun. Ko''krak qafasidagi og''riqni 1 dan 10 gacha baholang.',
     'scale_1_10',
     '{"min": 1, "max": 10}'),

    ('hasan', 5, 0, 'wellbeing',
     'Salom, Hasan! 5-kun. Umumiy ahvolingiz qanday? Holsizlik yoki bosh aylanishi bormi?',
     'free_text',
     '{"placeholder": "Masalan: holsizlik yo''q, yaxshiman"}');
